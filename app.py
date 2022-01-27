#inportando bibliotecas para o sistema WEB
from flask import Flask, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, LoginManager, logout_user, UserMixin
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import check_password_hash
from werkzeug.security import generate_password_hash
import requests

#importando bibliotecas para o sistema PlagDetect
import re
import os, os.path
import plotly.offline
import shutil

from flask import *
import plotly.graph_objects as go #nova importação
import numpy as np #nova importação
from tika import parser #nova importção
from nltk.tokenize import word_tokenize
from scipy.ndimage import gaussian_filter
from nltk.lm import MLE, WittenBellInterpolated
from nltk.util import ngrams, pad_sequence, everygrams
import nltk

import sklearn
from sklearn import tree

app = Flask(__name__)
app.config["DEBUG"] = True

#indicando a pasta em que os arquivos serão salvos:
UPLOAD_FOLDER = './uploads/'
RESULTADO_FOLDER = './resultados/'

#Atribuindo valores path para buscar arquivos:
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULTADO_FOLDER'] = RESULTADO_FOLDER

try:
    print("Connectando ao banco")
    app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://postgres:root@localhost:5432/plag"
    app.config["SQLALCHEMY_POOL_RECYCLE"] = 299
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db = SQLAlchemy(app)
    migrate = Migrate(app, db)
    app.secret_key = "SOMETHING RANDOM"
    login_manager = LoginManager()
    login_manager.init_app(app)
    print("Ok")
except:
    print("Erro")


class User(UserMixin, db.Model):

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(128))
    password_hash = db.Column(db.String(128))
    
    
    def check_password(self, password):
        return (password == self.password_hash)


    def get_id(self):
        return self.username



@login_manager.user_loader
def load_user(user_id):
    return User.query.filter_by(username=user_id).first()




@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_template("main_page.html")

    if not current_user.is_authenticated:
        return redirect(url_for('index'))


@app.route("/login/", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login_page.html", error=False)

    user = load_user(request.form["username"])
    if user is None:
        return render_template("login_page.html", error=True)

    if not user.check_password(request.form["password"]):
        return render_template("login_page.html", error=True)

    login_user(user)
    return redirect(url_for('index'))


@app.route('/resultado/', methods = ['POST'])
def success():
    if request.method == 'POST':
        #pegando o arquivo e salvando na pasta
        a = request.form.getlist('ano')
        f = request.files['file']
        f.save(os.path.join(app.config['UPLOAD_FOLDER'], f.filename))
        
        #analisando arquivos:
        ano_salvo = str(a[0])
        # resultado_analise = next(os.walk("./resultados/"))
        # path, dirs, files = next(os.walk("./projetos/"+ano_salvo+"/"))
        # file_count = len(files)
        texto = "./uploads/"+f.filename
        valores_maximos = []
        valores_medios = []
        valores_arquivo = []
        
        #################### LAÇO PARA API ####################
        def getArquivesData():
            file = requests.get("https://demo.dspace.org/rest/items")
            data = json.loads(file.text)
            return data
        def arquives():
            ids = []
            textosDSpace = []
            data = getArquivesData()
            j = 0
            for item in data:
                ids.append(item['uuid'])
            
            for idsItem in ids:
                file = requests.get('https://demo.dspace.org/rest/items/'+str(idsItem)+'/bitstreams')
                dataItem = json.loads(file.text)
                for itemPDF in dataItem:
                    if(itemPDF['mimeType'] == "application/pdf"):
                        arquive = requests.get('https://demo.dspace.org/rest/bitstreams/'+str(itemPDF['uuid'])+'/retrieve', allow_redirects=True)
                        open('./ArquivosDSpace/'+str(itemPDF['uuid'])+'.pdf', 'wb').write(arquive.content)
                        texto_salvo = parser.from_file("./ArquivosDSpace/"+str(itemPDF['uuid'])+".pdf")
                        train_text = texto_salvo['content']
                        os.remove("./ArquivosDSpace/"+str(itemPDF['uuid'])+".pdf")
                        #Variaveis:
                        texto = "./uploads/"+f.filename
                        texto_fornecido = parser.from_file(texto)

                        #Fornecendo dados para a variável "train_text" com o valor de "texto_salvo" para posteriormente ser analisado
                        train_text = texto_salvo['content']
                        # aplique o pré-processamento (remova o texto entre colchetes e chaves e rem punc)
                        train_text = re.sub(r"\[.*\]|\{.*\}", "", train_text)
                        train_text = re.sub(r'[^\w\s]', "", train_text)

                        # definir o número ngram
                        n = 5

                        # preencher o texto e tokenizar
                        training_data = list(pad_sequence(word_tokenize(train_text), n,
                                                            pad_left=True,
                                                            left_pad_symbol="<s>"))

                        # gerar ngrams
                        ngrams = list(everygrams(training_data, max_len=n))

                        # build ngram language models
                        model = WittenBellInterpolated(n)
                        model.fit([ngrams], vocabulary_text=training_data)

                        #Fornecendo dados para a variável "testt_text" com o valor de pdf2_test para posteriormente ser comparado com o arquivo de treinamento
                        test_text = texto_fornecido['content']
                        test_text = re.sub(r'[^\w\s]', "", test_text)

                        # Tokenize e preencha o texto
                        testing_data = list(pad_sequence(word_tokenize(test_text), n,
                                                            pad_left=True,
                                                            left_pad_symbol="<s>"))

                        # atribuir pontuações
                        scores = []
                        for i, item in enumerate(testing_data[n-1:]):
                            s = model.score(item, testing_data[i:i+n-1])
                            scores.append(s)

                        scores_np = np.array(scores)

                        # definir largura e altura
                        width = 8
                        height = np.ceil(len(testing_data)/width).astype("int64")

                        # copiar pontuações para matriz em branco retangular
                        a = np.zeros(width*height)
                        a[:len(scores_np)] = scores_np
                        diff = len(a) - len(scores_np)

                        # aplique suavização gaussiana para estética
                        a = gaussian_filter(a, sigma=1.0)

                        # remodelar para caber no retângulo
                        a = a.reshape(-1, width)

                        # rótulos de formato
                        labels = [" ".join(testing_data[i:i+width]) for i in range(n-1, len(testing_data), width)]
                        labels_individual = [x.split() for x in labels]
                        labels_individual[-1] += [""]*diff
                        labels = [f"{x:60.60}" for x in labels]

                        # criar mapa de calor para colocar no resultado visual
                        # fig = go.Figure(data=go.Heatmap(
                        #                 z=a, x0=0, dx=1,
                        #                 y=labels, zmin=0, zmax=1,
                        #                 customdata=labels_individual,
                        #                 hovertemplate='%{customdata} <br><b>Pontuacao:%{z:.3f}<extra></extra>',
                        #                 colorscale="burg"))
                        # fig.update_layout({"height":height*40, "width":1000, "font":{"family":"Courier New"}})
                        #criando resultado visual:
                        #plotly.offline.plot(fig, filename='/home/Allberson/mysite/resultados/resultado.html', auto_open=False)

                        #Armazenando dados dos scores para mostrar posteriormente
                        valores_scores = np.array(scores)

                        features = [[1],
                                [0.90], 
                                [0.70], 
                                [0.60],
                                [0.50],
                                [0.40],
                                [0.30]]
                        labels = [
                                "Plágio total", 
                                "Nível máximo", 
                                "Nível máximo/moderado", 
                                "Nível moderado", 
                                "Nível moderado/baixo", 
                                "Nível Baixo", 
                                "Nível Sem plágio"
                                ]
                        clf = tree.DecisionTreeClassifier()
                        clf = clf.fit(features, labels)
                        nivel = (clf.predict(X = [[valores_scores.max]]))

                        valores_arquivo.insert(j, itemPDF['uuid'])
                        j = j + 1
        arquives()
        #buscando arquivo com maior nível igualdade:
        val_maximo = np.array(valores_maximos)
        val_medio = np.array(valores_medios)
        busc_val_max = 1090
        busc_val_med = 500
        maxx = np.where(val_maximo > busc_val_max)[0]
        medd = np.where(val_medio > busc_val_med)[0]

        #Iniciando a página web
        if len(maxx) == 0:
           ano = ano_salvo
           resultado_false = "Nenhum arquivo encontrado que se iguale com o seu"
           os.remove('./uploads/'+f.filename) #removendo arquivo enviado pelo usuário
           return render_template("resultado_page.html", name = f.filename, resultado_neg = resultado_false, valor_ano = ano)
        elif len(maxx) > 0:
            ano = ano_salvo
            tot_projetos = 2
            resultado_mensagem = 'Encontramos um projeto com uma grande similaridade.'
            valor = "80%"
            enc = "Encontramos alguns projetos tiveram resultados positivos no momento de nossa análise. Veja a tabela abaixo"
            projetos_nomes_ok = 2
            mens = "O(s) projeto(s) analisado(s) pode/podem ter um valor igual ou superior ao mostrado na coluna 'valor de cópia' : "
            os.remove('./uploads/'+f.filename)
            return render_template("resultado_page.html", name = f.filename, mensagem = mens,resultado_men = resultado_mensagem, resultado_proj = projetos_nomes_ok, resultado_max = valor, encontrado = enc, valor_ano = ano, tot_proj = tot_projetos)

#Saindo da conta
@app.route("/logout/")
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

app.run()