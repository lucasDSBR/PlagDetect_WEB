# Importando o CountVectorizer
from sklearn.feature_extraction.text import CountVectorizer
# Importando o NLTK
import nltk
# Carregando a base de dados
from nltk.corpus import webtext
import numpy as np
def remItemNull(text):
    list = []
    breakPartsText = text.split('\n')
    for i in breakPartsText:
        if(i != ''):
            if(i != ' '):
                list.append(i)
    return list
            
def PreProcess(text):
    textOk = remItemNull(text)
    
    #Create object vectorizated
    vectorizer = CountVectorizer()
    
    #Apply the vectorizer in data
    vectorizer.fit(textOk)
    
    #Apply transform
    matrix = vectorizer.transform(textOk)
    
    teste = matrix.toarray()
    teste2 = teste
    