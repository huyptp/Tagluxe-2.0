"""Build a migration SQLite file from read-only admin exports; never edits the live shop."""
import argparse
import csv
from datetime import datetime, date
import json
from pathlib import Path
import sqlite3
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy import create_engine, select, func
from backend.database import db
from backend import models


def build(root, output, local_backup):
    load=lambda name:json.loads((root/name).read_text(encoding='utf-8'))
    engine=create_engine('sqlite:///'+str(output.resolve()).replace('\\','/'))
    db.metadata.create_all(engine)
    with engine.connect() as connection:
        if any(connection.execute(select(func.count()).select_from(table)).scalar_one() for table in db.metadata.sorted_tables):
            raise RuntimeError('Snapshot destination already contains records.')
    local=create_engine('sqlite://',creator=lambda:sqlite3.connect('file:'+local_backup.resolve().as_posix()+'?mode=ro',uri=True))
    with local.connect() as old:
        markers=[dict(row) for row in old.execute(select(models.SchemaMigration.__table__)).mappings()]
        compatibility=[dict(row) for row in old.execute(select(models.PriceTier.__table__).where(models.PriceTier.category.in_(['pvc','combo']))).mappings()]
        local_products={row['id']:dict(row) for row in old.execute(select(models.Product.__table__)).mappings()}
    public_by_id={row['id']:row for row in load('accessories-public.json')['data']['raw_list']}
    specs={row['id']:row for row in load('product-specs.json')}
    products=[]
    for row in load('products.json'):
        products.append({key:row[key] for key in ('id','name','category','description','price_type','width')} | {
            'images_json':json.dumps(row['images'],ensure_ascii=False),'featured':bool(row['featured']),
            'visible':bool(row['visible']),'price':int(row['price']),'min_order':int(row['min_order']),
            'material':local_products.get(row['id'],{}).get('material',''),
            'badge':specs[row['id']]['badge'],'specs_json':json.dumps(specs[row['id']]['specs'],ensure_ascii=False)})
    accessories=[]
    for row in load('accessories.json'):
        row['title']=public_by_id.get(row['id'],{}).get('title',row['name']);accessories.append(row)
    settings=[{'key':key,'value_json':json.dumps(load(file)['data'],ensure_ascii=False)} for key,file in [('demo_images','demo-images.json'),('campaign_banner','campaign-banner.json')]]
    with (root/'quotes.csv').open(encoding='utf-8-sig',newline='') as source:
        csv_rows=list(csv.DictReader(source))
    quotes=[]
    for row in csv_rows:
        quotes.append({'id':row['Mã Báo Giá'],'created_at':datetime.strptime(row['Thời Gian Tạo'],'%d/%m/%Y %H:%M:%S'),
            'customer_name':row['Tên Khách Hàng'],'phone':row['Số Điện Thoại'].lstrip("'"),'category':row['Dòng Sản Phẩm'],
            'specs':row['Quy Cách / Kích Thước'],'punched_hole':{'Lỗ tròn':'round','Lỗ con nhộng':'capsule'}.get(row['Đục Lỗ'],'none'),
            'accessories':row['Phụ Kiện Kèm Theo'],'quantity':int(row['Số Lượng']),'unit_price':int(row['Đơn Giá (VNĐ)']),
            'include_vat':row['VAT 8%']=='Có (8%)','vat_amount':int(row['Tiền VAT (VNĐ)']),
            'total_price':int(row['Tổng Thành Tiền (VNĐ)']),'status':row['Trạng Thái Xử Lý'],
            'sync_status':row['Đồng Bộ Google Sheets'],'notes':row['Ghi Chú'],'retry_count':0})
    workflows=[]
    for row in load('quote-workflow.json'):
        if row['owner'] or row['internal_notes'] or row['follow_up_on'] or row['priority']!='normal':
            workflows.append(row|{'updated_by':'admin','updated_at':datetime.now(),
                'follow_up_on':date.fromisoformat(row['follow_up_on']) if row['follow_up_on'] else None})
    logs=load('audit-log-visible.json')
    for row in logs:row['timestamp']=datetime.strptime(row['timestamp'],'%d/%m/%Y %H:%M:%S')
    payloads=[(models.SchemaMigration,markers),(models.PriceTier,load('price-tiers.json')+compatibility),
        (models.Product,products),(models.Accessory,accessories),(models.SiteSetting,settings),
        (models.Quote,quotes),(models.QuoteAdminState,workflows),(models.AuditLog,logs)]
    with engine.begin() as connection:
        for model,rows in payloads:
            if rows:connection.execute(model.__table__.insert(),rows)
    manifest={'source':'Read-only live admin/public snapshots, not a raw production database dump',
        'counts':{model.__tablename__:len(rows) for model,rows in payloads},
        'legacy_price_tiers_from_local_backup':len(compatibility),
        'unavailable_internal_data':['original idempotency responses','original queue leases','original audit IPs'],
        'material_field_source':'Local backup for a product field not exposed by the admin form',
        'outbound_quote_tasks_created':False}
    (root/'snapshot-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Prepared snapshot row counts:',manifest['counts'])
    engine.dispose();local.dispose()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot-dir',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--local-backup',required=True,type=Path)
    args=parser.parse_args()
    build(args.snapshot_dir,args.output,args.local_backup)
