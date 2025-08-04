from flask import Flask, render_template, request, redirect, url_for
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Sample data storage (replace with database in production)
ads = []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit_ad', methods=['GET', 'POST'])
def submit_ad():
    if request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        description = request.form['description']
        file = request.files['image']
        if file:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            ads.append({'name': name, 'price': price, 'description': description, 'image': filename})
        return redirect(url_for('view_ads'))
    return render_template('submit_ad.html')

@app.route('/view_ads')
def view_ads():
    return render_template('view_ads.html', ads=ads)

@app.route('/currency_analysis')
def currency_analysis():
    return render_template('currency_analysis.html')

@app.route('/signals')
def signals():
    return render_template('signals.html')

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)
