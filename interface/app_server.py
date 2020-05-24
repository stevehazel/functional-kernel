from uuid import uuid4
from flask import Flask, render_template, session

from util import is_uuid

app = Flask(__name__)
app.debug = True
app.config['SECRET_KEY'] = 'secret!'


@app.route('/node/<node_uuid>')
def index(node_uuid):
    if not is_uuid(node_uuid):
        raise Exception('UUID required')

    session_id = session.get('SessionID')
    if not session_id:
        session_id = str(uuid4())
        session['SessionID'] = session_id

    return render_template('index.html', **{
        'SessionID': session_id,
        'NodeUUID': node_uuid
    })


if __name__ == '__main__':
    try:
        app.run(debug=True, host='0.0.0.0', port=7010, threaded=True, use_reloader=False)
    except Exception as e:
        print(e)
