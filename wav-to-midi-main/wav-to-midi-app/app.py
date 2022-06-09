from ast import Try
from flask import Flask, render_template, request, send_file
import requests
from handlers.handlers import Convert

# initialize flask app
app = Flask(__name__)

# prevent caching file for development


@app.after_request
def add_header(r):
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    r.headers['Cache-Control'] = 'public, max-age=0'
    return r


# render HTML page
@app.route('/')
def upload_file_page():
    return render_template('./upload.html')


# upload method when file is uploaded
@app.route('/uploader', methods=['GET', 'POST'])
def upload_file():
    # get uploaded file
    try:
        uploaded_file = request.files['file']
        # file_name = str(uuid.uuid4()) + uploaded_file.filename
        if uploaded_file.filename != '':
            # check if the uploaded file is a wav file
            split = uploaded_file.filename.split('.')
            if split.__len__() == 2 and split[1] == 'wav':
                # get file name and add .wav extension
                file_name = uploaded_file.filename.split('.')[0]
                uploaded_file.save(file_name + ".wav")
                # convert file to midi format and download to front-end
                Convert.convert_file(file_name + ".wav", file_name + ".mid")
                return send_file(path_or_file=file_name + ".mid", mimetype="audio/midi", as_attachment=True)
        return "Error in the uploaded file", 400
    except:
        return "Error in the uploaded file", 400


# uplod method when link is uploaded
@app.route('/upload_wav_link', methods=['GET', 'POST'])
def upload_wav_link():
    # fetch the link, download the file, and convert to midi format
    url = request.form['wavLink']
    r = requests.get(url, allow_redirects=True)
    open('wav_file.wav', 'wb').write(r.content)
    Convert.convert_file("wav_file.wav", "wav_file.mid")
    # send the midi file to frontend for download
    return send_file(path_or_file="wav_file.mid", mimetype="audio/midi", as_attachment=True)


# run the application server
if __name__ == "__main__":
    app.run()
