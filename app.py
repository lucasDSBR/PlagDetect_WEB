#inportando bibliotecas para o sistema WEB
from flask import Flask, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, LoginManager, logout_user, UserMixin
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import check_password_hash

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



app = Flask(__name__)
app.config["DEBUG"] = True

#indicando a pasta em que os arquivos serão salvos:
UPLOAD_FOLDER = '/home/{nome_de_usuario}/mysite/uploads/'
RESULTADO_FOLDER = '/home/{nome_de_usuario}/mysite/resultados/'

#Atribuindo valores path para buscar arquivos:
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULTADO_FOLDER'] = RESULTADO_FOLDER


SQLALCHEMY_DATABASE_URI = "mysql+mysqlconnector://{nome_de_usuario}:{senha_do_banco_de_dados}@{nome_de_usuario}.mysql.pythonanywhere-services.com/{nome_de_usuario}${nome_do_banco_de_dados}".format(
    username="SOMETHING",
    password="SOMETHINGELSE",
    hostname="SOMETHING.mysql.pythonanywhere-services.com",
    databasename="SOMETHING$comments",
)
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_POOL_RECYCLE"] = 299
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)
app.secret_key = "SOMETHING RANDOM"
login_manager = LoginManager()
login_manager.init_app(app)


class User(UserMixin, db.Model):

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(128))
    password_hash = db.Column(db.String(128))

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


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
        resultado_analise = next(os.walk("/home/{nome_de_usuario}/mysite/resultados/"))
        path, dirs, files = next(os.walk("/home/{nome_de_usuario}/mysite/projetos/"+ano_salvo+"/"))
        file_count = len(files)
        texto = "/home/{nome_de_usuario}/mysite/uploads/"+f.filename
        valores_maximos = []
        valores_medios = []
        valores_arquivo = []

        j = 0
        while j < file_count:
            #Variaveis:
            texto = "/home/{nome_de_usuario}/mysite/uploads/"+f.filename
            texto_salvo = parser.from_file("/home/{nome_de_usuario}/mysite/projetos/"+ano_salvo+"/"+files[j])
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
            fig = go.Figure(data=go.Heatmap(
                            z=a, x0=0, dx=1,
                            y=labels, zmin=0, zmax=1,
                            customdata=labels_individual,
                            hovertemplate='%{customdata} <br><b>Pontuacao:%{z:.3f}<extra></extra>',
                            colorscale="burg"))
            fig.update_layout({"height":height*40, "width":1000, "font":{"family":"Courier New"}})
            #criando resultado visual:
            #plotly.offline.plot(fig, filename='/home/Allberson/mysite/resultados/resultado.html', auto_open=False)
            
            #Armazenando dados dos scores para mostrar posteriormente
            valores_scores = np.array(scores)

            #Atribuindo valores para propor condições de valores:
            buscar_max = 0.9000000000000000 #Nivel alto de plágio

            buscar_med = 0.8000000000000000 #Nível acima da média

            #atribuindo valores mais autos de cópia
            maximo = np.where(valores_scores > buscar_max)[0]
            medio = np.where(valores_scores > buscar_med)[0] #Nao ustilizado no momento
            valores_maximos.insert(j, len(maximo))
            valores_medios.insert(j, len(medio)) #Nao ustilizado no momento
            valores_arquivo.insert(j, files[j])

            j = j + 1

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
           os.remove('/home/{nome_de_usuario}/mysite/uploads/'+f.filename) #removendo arquivo enviado pelo usuário
           return render_template("resultado_page.html", name = f.filename, resultado_neg = resultado_false, valor_ano = ano)
        elif len(maxx) > 0:
            ano = ano_salvo
            tot_projetos = file_count
            resultado_mensagem = 'Encontramos um projeto com uma grande similaridade.'
            valor = "80%"
            enc = "Encontramos alguns projetos tiveram resultados positivos no momento de nossa análise. Veja a tabela abaixo"
            projetos_nomes_ok = files[int(maxx)]
            mens = "O(s) projeto(s) analisado(s) pode/podem ter um valor igual ou superior ao mostrado na coluna 'valor de cópia' : "
            os.remove('/home/{nome_de_usuario}/mysite/uploads/'+f.filename)
            return render_template("resultado_page.html", name = f.filename, mensagem = mens,resultado_men = resultado_mensagem, resultado_proj = projetos_nomes_ok, resultado_max = valor, encontrado = enc, valor_ano = ano, tot_proj = tot_projetos)

#Saindo da conta
@app.route("/logout/")
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))