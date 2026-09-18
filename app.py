import os
from backend import create_app
import backend.services.data_service as data_service

# Khởi tạo ứng dụng từ Application Factory (Backend Package)
app = create_app()

# Expose các hàm phục vụ tương thích ngược cho test suites & toolscripts
load_data = data_service.load_data
save_data = data_service.save_data
product_schema = data_service.product_schema

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, port=port)
