#!/usr/bin/python
#-*-coding:utf-8-*-

import urllib2
import re
import time
import atexit
import numpy as np
from pymongo import MongoClient
from beebotte import *
from flask import Flask, render_template, request, redirect, Response
from apscheduler.schedulers.background import BackgroundScheduler


app=Flask(__name__)
API_KEY = '2f0faaff5ddc696b10897112e7102c44'
SECRET_KEY = '88e0cde008f1fa4b1213169793b4968b0fe42056212917a9b972cd389601bf05'
MEDIAcalcular = 0


def numero_fecha():
	global mostrarNUMERO
	global mostrarHORA
	#Acceder a la página web y coger nº aleatorio
	paginaNumeros = urllib2.urlopen ("http://www.numeroalazar.com.ar/")
	numeros = paginaNumeros.read()
	mostrarNumero = re.findall ("\d+\.\d*",numeros)
	#Representar fecha y hora de acceso al nº aleatorio	
	localtime = time.asctime(time.localtime(time.time()))
	hora = localtime
	#Almacenar en variables
	mostrarNUMERO = str(mostrarNumero[4])
	mostrarHORA = str(hora)
	#Creación de la base de datos interna MONGO
	conn = MongoClient()
	db=conn.basedatosv3
	entrada = { 'numero aleatorio': float(mostrarNUMERO),
		    'conexion': mostrarHORA}
	NumAleatorio = db.NumAleatorio
	NumAleatorio.insert(entrada)
	#Creación de la base de datos externa BEEBOTTE
	conn_beebotte = BBT(API_KEY,SECRET_KEY)
	entrada_numeros_bbt = Resource(conn_beebotte,'numeros_azar','numeros_beebotte')
	entrada_bbt = (float(mostrarNUMERO))
	entrada_numeros_bbt.write(entrada_bbt)
	#Representar por terminal cada acceso a un nº nuevo
	print entrada_bbt,str(hora)
	#Realizar comparación entre el nuevo número obtenido y el umbral Actual introducido
	if (float(mostrarNUMERO) > float(umbralActual)):
		print "CUIDADIIIITOOO!!", mostrarNUMERO, mostrarHORA


def calculo_media_interna():
	global media_mostrar
	media_mostrar=None
	#Creación de la base de datos interna MONGO e imprimir por la web
	conn = MongoClient()
	db=conn.basedatosv3
	NumAleatorio = db.NumAleatorio
	media = db.NumAleatorio.aggregate([{"$group":{"_id": None, "media": {"$avg": '$numero aleatorio'}}}])
	for pMedia in media:
		media_mostrar = ('%0.2f' %(pMedia["media"]))


def calculo_media_externa():
	global media_bbt
	lista_beebotte = []
	#Creación de la base de datos exterba BEEBOTTE e imprimir por la web 
	conn_beebotte = BBT(API_KEY,SECRET_KEY)
	entrada_numeros_bbt = Resource(conn_beebotte,'numeros_azar','numeros_beebotte')
	lista_numero = entrada_numeros_bbt.read(limit =20000)
	for pMedia_bbt in lista_numero:	
		lista_beebotte.append (pMedia_bbt["data"])
	#Calcular media de la lista de nº Beebotte
	media_aux = np.mean(lista_beebotte) 
	media_bbt = '%0.2f' %(media_aux)


def calculo_umbral(): 
	global listamayor
	global listamenor	
	listaMAYOR=[]
	listaMENOR=[]
	#Acceder a la base de datos Mongodb
	conn = MongoClient()
	db=conn.basedatosv3
	NumAleatorio = db.NumAleatorio
	#Imprimir números SUPERIORES al umbral
	umbralSup = NumAleatorio.find({"numero aleatorio":{"$gt":float(umbralHist)}})
	for pSup in umbralSup:
		numerosSUP = ('numero aleatorio: %0.2f conexion: %s' %(pSup["numero aleatorio"],pSup["conexion"]))
		listaMAYOR.append (numerosSUP)
	listamayor=listaMAYOR[(len(listaMAYOR)-2):]
	#Imprimir números INFERIORES al umbral  
	umbralInf = NumAleatorio.find({"numero aleatorio":{"$lt":float(umbralHist)}})
	for pInf in umbralInf:
		numerosINF = ('numero aleatorio: %0.2f conexion: %s' %(pInf["numero aleatorio"],pInf["conexion"]))
		listaMENOR.append (numerosINF)
	listamenor=listaMENOR[(len(listaMENOR)-2):]	
		#print ('numero aleatorio: %0.2f conexion: %s' %(pInf["numero aleatorio"],pInf["conexion"]))


def event_stream():
	if (float(mostrarNUMERO) > float(umbralActual)):
		print "CUIDADIIIITOOO!!", mostrarNUMERO, mostrarHORA
		numero = {"tipo": "numero", "valor": float(mostrarNUMERO)}
		data_json_num = json.dumps(numero)
		umbral = {"tipo": "umbral", "valor": float(umbralActual)}
		data_json_umb = json.dumps(umbral)
		yield '%s' %str(data_json_num)


@app.route('/',methods=['GET','POST'])
def index():
	global umbralHist
	global umbralActual
	global MEDIAcalcular
	#Método POST para los botones
	if request.method == 'POST':
		valor = request.form['form1']
		if valor == 'Media':
			if MEDIAcalcular == 0:
				calculo_media_externa()
				MEDIAcalcular = 1
				print "BASE EXTERNA la media calculada es:  "+str(media_bbt)
				return render_template ('pagina.html',media_ext_WEB=media_bbt)
			else:
				calculo_media_interna()
				MEDIAcalcular = 0
				print "BASE INTERNA la media calculada es:  "+media_mostrar
				return render_template ('pagina.html',media_int_WEB=media_mostrar)
		if valor == 'Graficas':
			return redirect('https://beebotte.com/dash/4ca98260-cefb-11e7-bfef-6f68fef5ca14#.WhSQjXAo-gA')
		if valor == 'Numero':
			numero_fecha()
			return render_template ('pagina.html',numeroAZAR=mostrarNUMERO, hora=mostrarHORA)
		if valor == 'Enviar':
			umbralHist = request.form['textHist']
			print "el umbral introducido es:  "+umbralHist
			calculo_umbral()
			return render_template ('pagina.html',superioresWEB=listamayor,inferioresWEB=listamenor)
		if valor == 'Aceptar':
			umbralActual = request.form['textAct']
			print "el umbral actual introducido es:  "+umbralActual
			return render_template ('pagina.html')

	else:
		return render_template ('pagina.html')


@app.route('/alerta')
def stream():
	return Response(event_stream(),mimetype="text/event-stream")


if __name__=='__main__':
	scheduler = BackgroundScheduler()
	scheduler.start()
 	scheduler.add_job(numero_fecha, 'interval', seconds=20)
	atexit.register(lambda: scheduler.shutdown())
	app.debug=True
	app.run(host='0.0.0.0')
