import requests
import json
import PyPDF2
from tika import parser #nova importção
import re
from datetime import date
import csv
# https://demo.dspace.org/rest/bitstreams/ecc84f10-527a-4d6e-bc5f-35f82c5fee26/retrieve

def getArquivesData():
    file = requests.get("http://localhost:8888/rest/items")
    data = json.loads(file.text)
    return data

def csvDataTreino(data):
    f = open('train.csv', 'w', newline='', encoding='utf-8')
    w = csv.writer(f)
    w.writerow(["id", "text_Train1"])
    for i in data:
        w.writerow([i['ArquivoTreino'], str(i['TextoTreino'])])
        
def preProcessamento(data):
    dataPreProcessada = []
    #Realizando pré-processamento
    for texto_t in data:
        train_text = re.sub(r"\[.*\]|\{.*\}", "", texto_t['TextoTreino'])
        train_text = re.sub(r'[^\w\s]', "", texto_t['TextoTreino'])
        dataPreProcessada.append({"ArquivoTreino": texto_t['ArquivoTreino'], "DataBusca": date.today(), "TextoTreino": train_text})
    csvDataTreino(dataPreProcessada)
    
def arquives():
    ids = []
    textosDSpace = []
    data = getArquivesData()
    
    for item in data:
        ids.append(item['uuid'])
    
    for idsItem in ids:
        file = requests.get('http://localhost:8888/rest/items/'+str(idsItem)+'/bitstreams')
        dataItem = json.loads(file.text)
        for itemPDF in dataItem:
            if(itemPDF['mimeType'] == "application/pdf"):
                arquive = requests.get('http://localhost:8888/rest/bitstreams/'+str(itemPDF['uuid'])+'/retrieve', allow_redirects=True)
                open('./ArquivosDSpace/'+str(itemPDF['uuid'])+'.pdf', 'wb').write(arquive.content)
                texto_salvo = parser.from_file("./ArquivosDSpace/"+str(itemPDF['uuid'])+".pdf")
                train_text = texto_salvo['content']
                textosDSpace.append({"ArquivoTreino": str(itemPDF['uuid']), "DataBusca": date.today(), "TextoTreino": train_text})
    preProcessamento(textosDSpace)
arquives()