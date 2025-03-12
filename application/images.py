from flask import Blueprint, request, send_file
from .utils import images_collection
from io import BytesIO

images_bp = Blueprint('images', __name__)

@images_bp.route('/images_data/', methods=['GET'])
def get_image():
    # 从请求参数中获取图片名
    image_name = request.args.get('name')
    if not image_name:
        return "未提供图片名", 400

    # 在数据库中查找对应的图片数据
    result = images_collection.find_one({"name": image_name})
    if not result:
        return "未找到对应的图片", 404

    # 获取图片的二进制数据
    image_data = result["data"]

    # 将二进制数据转换为文件对象
    image_file = BytesIO(image_data)
    image_file.seek(0)

    # 返回图片数据给前端
    return send_file(image_file, mimetype='image/svg+xml')