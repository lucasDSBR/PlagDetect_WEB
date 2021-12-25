import requests
import json
import PyPDF2
# https://demo.dspace.org/rest/bitstreams/ecc84f10-527a-4d6e-bc5f-35f82c5fee26/retrieve

def getArquivesData():
    file = requests.get("https://demo.dspace.org/rest/items")
    data = json.loads(file.text)
    return data
def arquives():
    ids = []
    textos = []
    data = getArquivesData()
    
    for item in data:
        ids.append(item['uuid'])
    
    for idsItem in ids:
        file = requests.get('https://demo.dspace.org/rest/items/'+str(idsItem)+'/bitstreams')
        dataItem = json.loads(file.text)
        for itemPDF in dataItem:
            if(itemPDF['mimeType'] == "application/pdf"):
                download = requests.get('https://demo.dspace.org/rest/bitstreams/'+str(itemPDF['uuid'])+'/retrieve', allow_redirects=True)
                open(str(itemPDF['uuid'])+'.pdf', 'wb').write(download.content)