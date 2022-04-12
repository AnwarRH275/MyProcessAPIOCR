from distutils.log import debug
from flask import Flask, json, request, jsonify,send_from_directory
import os
import urllib.request
from werkzeug.utils import secure_filename
import sys
from flask_cors import CORS
from os import listdir
from os.path import isfile, join
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
import re


from sqlite3 import *
from datetime import datetime
import os

app = Flask(__name__)
 
CORS(app)
app.secret_key = "MyProcessOCR.BPM24"
 
UPLOAD_FOLDER = 'UPLOAD_FOLDER'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['CORS_HEADERS'] = 'Content-Type'


# OCR Managemenent
custom_config = r'--oem 3 --psm 6'


def convertPdf2Img(path,fileName):
    images = convert_from_path(path+fileName)
    for i in range(len(images)):
#         thresh = 230
#         fn = lambda x : 255 if x < thresh else 0
#         images[i] = images[i].convert('L').point(fn, mode='1')
        images[i] = images[i].convert('1')
        
        images[i].save('image.jpg')
        #images[i] = images[i].convert('1')
        newfileName = fileName[:-4]+'.jpg'
        images[i].save(path+newfileName, 'JPEG')
    
    return newfileName

def extract_index(bd,keys,dictionnary,fournisseur):
    get_index = []
    count = 0 
    for key in keys:
        for item in dictionnary:
            if keys[key].replace(' ','') in dictionnary[item].replace(' ',''):
                #print(key+' : '+dictionnary[item])
                get_index.append({key:item})
                job = (count,item,key,fournisseur)
                addInderList(bd,job)
                count+=1
    return get_index

    
def indexation(path,nameFile):
    
    
    extract = pytesseract.image_to_string(Image.open(path+convertPdf2Img(path,nameFile)),config=custom_config)
    result=extract.split('\n')
    dictionnary = {}
    for index,element in enumerate(result):
        if element != '' :   
            dictionnary['index_'+str(index)] = element
    return dictionnary

def sendDataExtractor(NameFournisseur,bd,path,fileName):
    req = "select * from IndexOCR where nameFournisseur like '"+NameFournisseur+"'"
    getData = getDataIndexOCR(bd,req)

    dictionnary = indexation(path,fileName)
    #print(getData)
    sendData={}
    for item in getData:
        try:
            if '.' in dictionnary[item['indexer']] or ',' in dictionnary[item['indexer']]:
                if ',' in dictionnary[item['indexer']]:
                    print(re.findall("\d+\,\d+", dictionnary[item['indexer']])[0] )
                    sendData[item['champsIndex']]= re.findall("\d+\,\d+", dictionnary[item['indexer']])[0] 
                else:    
                    sendData[item['champsIndex']]= re.findall("\d+\.\d+", dictionnary[item['indexer']])[0]
            else:
                if 'Date'.lower() in str(dictionnary[item['indexer']]).lower() and '/' in dictionnary[item['indexer']]:
                    #print( dictionnary[item['indexer']]) 
                    sendData[item['champsIndex']] = re.findall("\d+\/\d+/\d+", dictionnary[item['indexer']])[0]
                else:
                    sendData[item['champsIndex']]= dictionnary[item['indexer']].replace('@ ','')
        except:
            sendData[item['champsIndex']] = ''
    return sendData
# Code API 
def creation(bd,req):
    c = connect(bd)
    cur = c.cursor()
    res = cur.execute(req)
   
    c.close()

    
def addFournisseur(bd,job):
    req = ''' INSERT INTO Fournisseur(id,name)
              VALUES(?,?) '''
    c = connect(bd)
    cur = c.cursor()
    res = cur.execute(req,job)
    c.commit()
    c.close()
    
def addInderList(bd,job):
    req = ''' INSERT INTO IndexOCR(id,indexer,champsIndex,nameFournisseur)
              VALUES(?,?,?,?) '''
    c = connect(bd)
    cur = c.cursor()
    res = cur.execute(req,job)
    c.commit()
    c.close()
    
def getDataFournisseur(bd,req):
    allAPI = []
    c = connect(bd)
    cur = c.cursor()
    res = cur.execute(req)
    for ligne in res:
        api = {
                'id': ligne[0],
                'name': ligne[1]
            }
        allAPI.append(api)
    c.close()
    
    return allAPI   

def getDataIndexOCR(bd,req):
    allAPI = []
    c = connect(bd)
    cur = c.cursor()
    res = cur.execute(req)
    for ligne in res:
        api = {
                'id': ligne[0],
                'indexer': ligne[1],
                'champsIndex':ligne[2],
            'nameFournisseur':ligne[3]
            }
        allAPI.append(api)
    c.close()
    
    return allAPI  


#creation("MyProcessOCR2.sqlite",'''create table Fournisseur(id int,name str)''')
#creation("MyProcessOCR2.sqlite","create table IndexOCR(id int,indexer str,champsIndex str,nameFournisseur str)")
 
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])
 
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
 
@app.route('/')
def main():
    return 'Welcome To MyProcess OCR Api '

@app.route('/remove')
def removed():
    for filename in os.listdir(UPLOAD_FOLDER) :
        os.remove(UPLOAD_FOLDER + "/" + filename)
    return jsonify('All File Removed')


#@cross_origin(origin='149.202.73.148',headers=['Content-Type','Authorization'])
 
@app.route('/api', methods=['POST'])
def upload_file():
    # check if the post request has the file part
    if 'file' not in request.files:
        resp = jsonify({'message' : 'No file part in the request'})
        resp.status_code = 400
        return resp
 
    files = request.files.getlist('file')
    
    errors = {}
    success = False
     
    for file in files:      
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            success = True
            # Tratement fournisseur existant
            
            summary = sendDataExtractor('Genious Communications SARL',"MyProcessOCR3.sqlite",os.path.join(app.config['UPLOAD_FOLDER'],filename).replace(filename,''),filename)

        else:
            errors[file.filename] = 'File type is not allowed'
    
    if success and errors:
        errors['message'] = 'File(s) successfully uploaded'
        resp = jsonify(errors)
        resp.status_code = 500
        return resp
    if success:
        resp = jsonify(summary)

       # download_file(filename[:-4]+'')
        resp.status_code = 201
		
        return resp
    else:
        resp = jsonify(errors)
        resp.status_code = 500
        return resp
    
@app.route('/UPLOAD_FOLDER/<path:filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename, as_attachment=True)
 
	
if __name__ == '__main__':
	app.run(debug=True)
