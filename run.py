from application import create_app
import logging

if __name__ == '__main__':
    app = create_app()
    app.run(host="127.0.0.1", port=5050, debug=True)
else:
    app = create_app()
    gunicorn_logger = logging.getLogger("gunicorn.error")
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)