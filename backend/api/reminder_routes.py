"""Private scheduler RPC. Keys are never accepted in query strings."""
import secrets
from flask import request, jsonify
from backend.api.routes import api_bp
from backend.security import rate_limit
from backend.services import followup_reminders as reminders


@api_bp.route('/internal/follow-up-reminders',methods=['POST'])
@rate_limit(limit=30,window_sec=60)
def api_follow_up_reminders():
    key=reminders.scheduler_key()
    supplied=request.headers.get('Authorization','')
    expected='Bearer '+key
    if not key or len(supplied)>512 or not secrets.compare_digest(supplied.encode(),expected.encode()):
        response=jsonify(status='error',message='Unauthorized')
        response.status_code=401
    else:
        data=request.get_json(silent=True)
        if not isinstance(data,dict):
            response=jsonify(status='error',message='Invalid request');response.status_code=400
        elif data.get('action')=='prepare':
            response=jsonify(reminders.prepare())
        elif data.get('action') in ('ack','fail') and isinstance(data.get('batch_token'),str) and 20<=len(data['batch_token'])<=64:
            response=jsonify(reminders.finish(data['batch_token'],data['action']=='ack',data.get('error','mail')))
        else:
            response=jsonify(status='error',message='Invalid action');response.status_code=400
    response.headers['Cache-Control']='private, no-store'
    return response
