
# python.exe -m venv .venv
# cd .venv/Scripts
# activate.bat
# py -m ensurepip --upgrade
# pip install -r requirements.txt

from functools import wraps
from flask import Flask, render_template, request, jsonify, make_response, session, redirect, url_for
from equipos_service import equipos_bp

from flask_cors import CORS, cross_origin

import mysql.connector.pooling
import pusher
import pytz
import datetime

app = Flask(__name__)
app.secret_key = "clave_secreta"  # Puedes poner cualquier string aquí
app.config["SESSION_COOKIE_SECURE"] = False
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

CORS(app)


con_pool = mysql.connector.pooling.MySQLConnectionPool(
    pool_name="my_pool",
    pool_size=5,
    host="185.232.14.52",
    database="u760464709_23005014_bd",
    user="u760464709_23005014_usr",
    password="B|7k3UPs3&P"
)

app.register_blueprint(equipos_bp)

def pusherBase(channel, event, message="hello"):
    pusher_client = pusher.Pusher(
        app_id='2048639',
        key='85576a197a0fb5c211de',
        secret='bbd4afc18e15b3760912',
        cluster='us2',
        ssl=True
    )
    pusher_client.trigger(channel, event, {'message': message})
    return make_response(jsonify({}))

def pusherIntegrantes():
    return pusherBase("integranteschannel", "integrantesevent", "hello Integrantes")

def pusherEquiposIntegrantes():
    return pusherBase("equiposIntegranteschannel", "equiposIntegrantesevent", "hello Equipos Integrantes")

def pusherEquipos():
    return pusherBase("equiposchannel", "equiposevent", "hello Equipos")

def pusherProyectos():
    return pusherBase("proyectoschannel", "proyectosevent", "hello Proyectos")

def pusherProyectosAvances():
    return pusherBase("proyectosAvanceschannel", "proyectosAvancesevent", "hello Proyectos Avances")

def login(fun):
    @wraps(fun)
    def decorador(*args, **kwargs):
        if not session.get("login"):
            return jsonify({
                "estado": "error",
                "respuesta": "No has iniciado sesión"
            }), 401
        return fun(*args, **kwargs)
    return decorador

    
# Ruta de Inicio (Landin-Page)
@app.route("/")
def landingPage():
    return render_template("landing-page.html")

# Te regresa a (index)
@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/login")
def appLogin():
    return render_template("login.html")
    

# Funcionamiento del Inicio de sesion en base a lo llenado del formulario
@app.route("/iniciarSesion", methods=["POST"])
def iniciarSesion():
    
    usuario    = request.form["txtUsuario"]
    contrasena = request.form["txtContrasena"]
        
    con    = con_pool.get_connection()
    cursor = con.cursor(dictionary=True)
    sql    = """
    SELECT IdUsuario, Nombre, Tipo_Usuario
    FROM usuarios
            
    WHERE Nombre = %s 
    AND Contrasena = %s
    """
    val = (usuario, contrasena)
        
    cursor.execute(sql, val)
    registros = cursor.fetchall()
            
    if cursor:
        cursor.close()
    if con and con.is_connected():
        con.close()
            
    session["login"]      = False
    session["login-usr"]  = None
    session["login-tipo"] = 0
            
    if registros:
        usuario = registros[0]
        session["login"]      = True
        session["login-usr"]  = usuario["Nombre"]
        session["login-tipo"] = usuario["Tipo_Usuario"]
        return jsonify({
            "mensaje": "Inicio de sesión exitoso",
            "usuario": usuario
        })
    else:
        return jsonify({
            "error": "Credenciales incorrectas"
        }), 401

@app.route("/cerrarSesion", methods=["POST"])
@login
def cerrarSesion():
    session["login"]      = False
    session["login-usr"]  = None
    session["login-tipo"] = 0
    return make_response(jsonify({}))

@app.route("/preferencias")
@login
def preferencias():
    return make_response(jsonify({
        "usr": session.get("login-usr"),
        "tipo": session.get("login-tipo", 2)
    }))
    
#
#///////////////////////////// INTEGRANTES ///////////
#   Rutas  De  Integrantes    
@app.route("/integrantes")
@login
def integrantes():
    return render_template("integrantes.html")

# Traer los registros de integrantes en el tbody
@app.route("/tbodyIntegrantes")
@login
def tbodyProductos():
    try:
        con = con_pool.get_connection()
        cursor = con.cursor(dictionary=True)

        sql = """
        SELECT idIntegrante, nombreIntegrante
        FROM integrantes
        ORDER BY idIntegrante DESC
        LIMIT 10 OFFSET 0
        """
        cursor.execute(sql)
        registros = cursor.fetchall()

        return render_template("tbodyIntegrantes.html", integrantes=registros)

    except Exception as e:
        print("Error en /tbodyIntegrantes:", str(e))
        return jsonify({"error": "Error interno al cargar integrantes"}), 500

    finally:
        if cursor:
            cursor.close()
        if con and con.is_connected():
            con.close()


# Funcionamiento de la busuqeda de integrantes
@app.route("/integrantes/buscar", methods=["GET"])
@login
def buscarIntegrantes():
    args     = request.args
    busqueda = args["busqueda"]
    busqueda = f"%{busqueda}%"
    
    try:
        con    = con_pool.get_connection()
        cursor = con.cursor(dictionary=True)
        sql    = """
        
        SELECT idIntegrante,
               nombreIntegrante
    
        FROM integrantes
    
        WHERE nombreIntegrante LIKE %s
    
        ORDER BY idIntegrante DESC
        LIMIT 10 OFFSET 0
        """
        val = (busqueda,)

        cursor.execute(sql, val)
        registros = cursor.fetchall()

    except mysql.connector.errors.ProgrammingError as error:
        registros = []

    finally:
        if cursor:
            con.close()
        if con and con.is_connected():
            con.close()

    return make_response(jsonify(registros))

# Funionamiento de insertar integrantes
@app.route("/integrante", methods=["POST"])
@login
def guardarIntegrante():
    try:
        idIntegrante = request.form.get("idIntegrante", "").strip()
        nombreIntegrante = request.form.get("nombreIntegrante", "").strip()

        if not nombreIntegrante:
            return jsonify({"error": "Nombre del integrante requerido"}), 400

        con = con_pool.get_connection()
        cursor = con.cursor()

        if idIntegrante:
            sql = """
            UPDATE integrantes
            SET nombreIntegrante = %s
            WHERE idIntegrante = %s
            """
            val = (nombreIntegrante, idIntegrante)
        else:
            sql = """
            INSERT INTO integrantes (nombreIntegrante)
            VALUES (%s)
            """
            val = (nombreIntegrante,)

        cursor.execute(sql, val)
        con.commit()

        pusherIntegrantes()
        return jsonify({"mensaje": "Integrante guardado correctamente"})

    except Exception as e:
        print("Error al guardar integrante:", str(e))
        return jsonify({"error": "Error interno al guardar"}), 500

    finally:
        if cursor:
            cursor.close()
        if con and con.is_connected():
            con.close()

# Funcionamiento de modificar integrantes
@app.route("/integrante/<int:id>")
@login
def editarIntegrante(id):
    con    = con_pool.get_connection()
    cursor = con.cursor(dictionary=True)
    sql    = """
    
    SELECT idIntegrante, nombreIntegrante
    
    FROM integrantes
    
    WHERE idIntegrante = %s
    """
    val = (id,)

    cursor.execute(sql, val)
    registros = cursor.fetchall()
    
    if cursor:
        cursor.close()
    if con and con.is_connected():
        con.close()

    if registros:
        return make_response(jsonify(registros[0]))
    else:
        return jsonify({"error": "Integrante no encontrado"}), 404


# Funcionamiento de eliminar integrantes
@app.route("/integrante/eliminar", methods=["POST"])
@login
def eliminarIntegrante():
    try:
        id = request.form["id"]

        con = con_pool.get_connection()
        cursor = con.cursor()
        sql = "DELETE FROM integrantes WHERE idIntegrante = %s"
        val = (id,)

        cursor.execute(sql, val)
        con.commit()

        pusherIntegrantes()
        return make_response(jsonify({"mensaje": "Integrante Eliminado"}))

    except Exception as e:
        print("Error al eliminar integrante:", str(e))
        return jsonify({"error": "Error interno al eliminar"}), 500

    finally:
        if cursor:
            cursor.close()
        if con and con.is_connected():
            con.close()


#   Rutas  De  Proyectos Avances    
#   Rutas  De  Proyectos Avances    
@app.route("/proyectosavances")
@login
def proyectosavances():
    con = con_pool.get_connection()
    cursor = con.cursor(dictionary=True)
    # Funcion para inner join demiselctt
    sql = """
    SELECT idProyecto, tituloProyecto
    FROM proyectos
    ORDER BY tituloProyecto ASC
    """
    cursor.execute(sql)
    proyectos = cursor.fetchall()
    con.close()

    # funcion para mandarlos a la funcion lista deljsjsjs
    return render_template("proyectosavances.html", proyectos=proyectos)
@app.route("/proyectos/lista")
@login
def listaProyectos():
    try:
        con = con_pool.get_connection()
        cursor = con.cursor(dictionary=True)
        sql = """
        SELECT idProyecto, tituloProyecto
        FROM proyectos
        ORDER BY tituloProyecto ASC
        """
        cursor.execute(sql)
        proyectos = cursor.fetchall()
        con.close()
        
        return make_response(jsonify(proyectos))
        
    except Exception as e:
        return make_response(jsonify({"error": str(e)}), 500)

@app.route("/tbodyProyectosAvances")
@login
def tbodyProyectosAvances():
    con = con_pool.get_connection()
    cursor = con.cursor(dictionary=True)
    sql = """
    SELECT pa.idProyectoAvance,
           pa.idProyecto,   
           pa.progreso,
           pa.descripcion,
           pa.fechaHora,
           p.tituloProyecto
    FROM proyectosavances pa
    INNER JOIN proyectos p ON pa.idProyecto = p.idProyecto
    ORDER BY pa.idProyectoAvance DESC
    LIMIT 10 OFFSET 0
    """
    cursor.execute(sql)
    registros = cursor.fetchall()
    con.close()
    
    return render_template("tbodyProyectosAvances.html", proyectosavances=registros)


@app.route("/proyectoavance", methods=["POST"])
@login
def guardarProyectoAvance():
    con = con_pool.get_connection()
    idProyectoAvance = request.form.get("idProyectoAvance")
    idProyecto       = request.form.get("idProyecto")  
    progreso         = request.form.get("txtProgreso")
    descripcion      = request.form.get("txtDescripcion")

    cursor = con.cursor()

    if idProyectoAvance:  # Update
        sql = """
        UPDATE proyectosavances
        SET idProyecto = %s,
            progreso   = %s,
            descripcion = %s,
            fechaHora = NOW()
        WHERE idProyectoAvance = %s
        """
        val = (idProyecto, progreso, descripcion, idProyectoAvance)
    else:  # Insert
        sql = """
        INSERT INTO proyectosavances (idProyecto, progreso, descripcion, fechaHora)
        VALUES (%s, %s, %s, NOW())
        """
        val = (idProyecto, progreso, descripcion)

    cursor.execute(sql, val)
    con.commit()
    con.close()

    pusherProyectosAvances()
    return make_response(jsonify({"mensaje": "Proyecto Avance guardado"}))


@app.route("/proyectoavance/eliminar", methods=["POST"])
@login
def eliminarProyectoAvance():
    con = con_pool.get_connection()
    id = request.form.get("id")

    cursor = con.cursor(dictionary=True)
    sql = """
    DELETE FROM proyectosavances 
    WHERE idProyectoAvance = %s
    """
    val = (id,)
    
    cursor.execute(sql, val)
    con.commit()
    con.close()

    pusherProyectosAvances()
    return make_response(jsonify({"mensaje": "Proyecto Avance eliminado"}))

#/////////////////////Equipos/////////////////////////////
  
#/// Lo borre pk no se comentar

#////////////////////////////////////////////////////    


@app.route("/proyectos")
@login
def proyectos():
    return render_template("proyectos.html")

@app.route("/tbodyProyectos")
@login
def tbodyProyectos():
    try:
        con = con_pool.get_connection()
        cursor = con.cursor(dictionary=True)
        sql = """
        SELECT 
            p.idProyecto,
            p.tituloProyecto,
            e.nombreEquipo,
            p.objetivo,
            p.estado
        FROM proyectos AS p
        INNER JOIN equipos AS e ON p.idEquipo = e.idEquipo
        ORDER BY p.estado DESC
        LIMIT 10 OFFSET 0
        """
        cursor.execute(sql)
        registros = cursor.fetchall()
        
        return render_template("tbodyProyectos.html", proyectos=registros)
    
    finally:
        if cursor:
            cursor.close()
        if con and con.is_connected():
            con.close()

@app.route("/proyectos/buscar", methods=["GET"])
@login
def buscarProyectos():
    args = request.args
    busqueda = args["busqueda"]
    busqueda = f"%{busqueda}%"

    try:
        con = con_pool.get_connection()
        cursor = con.cursor(dictionary=True)
        sql = """
        SELECT p.idProyecto, p.tituloProyecto, e.nombreEquipo, p.objetivo, p.estado
        FROM proyectos AS p
        INNER JOIN equipos AS e ON p.idEquipo = e.idEquipo
        WHERE p.tituloProyecto LIKE %s
        ORDER BY p.estado DESC
        LIMIT 10 OFFSET 0
        """
        val = (busqueda,)
        cursor.execute(sql, val)
        registros = cursor.fetchall()
        
        return make_response(jsonify(registros))

    except mysql.connector.errors.ProgrammingError as error:
        print(f"Error en búsqueda: {error}")
        return make_response(jsonify([]))

    finally:
        if cursor:
            cursor.close()
        if con and con.is_connected():
            con.close()

@app.route("/proyectos", methods=["POST"])
@login
def guardarProyectos():
    try:
        con = con_pool.get_connection()
        
        idProyecto = request.form.get("idProyecto", "").strip()
        tituloProyecto = request.form["tituloProyecto"]
        idEquipo = request.form["idEquipo"]
        objetivo = request.form["objetivo"]
        estado = request.form["estado"]
        
        cursor = con.cursor()

        if idProyecto:
            sql = """
            UPDATE proyectos
            SET tituloProyecto = %s,
                idEquipo = %s,
                objetivo = %s,
                estado = %s
            WHERE idProyecto = %s
            """
            val = (tituloProyecto, idEquipo, objetivo, estado, idProyecto)
        else:
            sql = """
            INSERT INTO proyectos (tituloProyecto, idEquipo, objetivo, estado)
            VALUES (%s, %s, %s, %s)
            """
            val = (tituloProyecto, idEquipo, objetivo, estado)

        cursor.execute(sql, val)
        con.commit()

        pusherProyectos()
        return make_response(jsonify({"mensaje": "Proyecto guardado"}))
    
    finally:
        if cursor:
            cursor.close()
        if con and con.is_connected():
            con.close()

@app.route("/proyectos/eliminar", methods=["POST"])
@login
def eliminarProyecto():
    try:
        con = con_pool.get_connection()
        id = request.form.get("id")

        cursor = con.cursor(dictionary=True)
        sql = """
        DELETE FROM proyectos
        WHERE idProyecto = %s
        """
        val = (id,)

        cursor.execute(sql, val)
        con.commit()
        
        pusherProyectos()
        
        return make_response(jsonify({"mensaje": "Proyecto eliminado correctamente"}))
        
    except mysql.connector.Error as error:
        con.rollback()
        print(f"Error al eliminar proyecto: {error}")
        return make_response(jsonify({"error": "Error al eliminar proyecto"}), 500)
        
    finally:
        if cursor:
            cursor.close()
        if con and con.is_connected():
            con.close()

@app.route("/proyectos/<int:id>", methods=["GET"])
@login
def obtenerProyecto(id):
    try:
        con = con_pool.get_connection()
        cursor = con.cursor(dictionary=True)
        sql = """
        SELECT 
            p.idProyecto,
            p.tituloProyecto,
            p.idEquipo,
            p.objetivo,
            p.estado,
            e.nombreEquipo
        FROM proyectos AS p
        INNER JOIN equipos AS e ON p.idEquipo = e.idEquipo
        WHERE p.idProyecto = %s
        """
        val = (id,)
        
        cursor.execute(sql, val)
        proyecto = cursor.fetchone()
        
        return make_response(jsonify(proyecto))
    
    finally:
        if cursor:
            cursor.close()
        if con and con.is_connected():
            con.close()

@app.route("/equipos/lista")
@login
def cargarEquipos():
    try:
        con = con_pool.get_connection()
        cursor = con.cursor(dictionary=True)
        sql = """
        SELECT idEquipo, nombreEquipo
        FROM equipos
        ORDER BY nombreEquipo ASC
        """
        
        cursor.execute(sql)
        registros = cursor.fetchall()
        
        return make_response(jsonify(registros))
    
    finally:
        if cursor:
            cursor.close()
        if con and con.is_connected():
            con.close()



#//////////////esta wea me trae una lista pal inerjoin //////////////////////////////////////////////////////////

#////////////////////////////////////////////////////////////////////////////////////////////////////////////////

@app.route("/equiposintegrantes")
@login
def equiposintegrantes():
    return render_template("equiposintegrantes.html")

@app.route("/tbodyEquiposIntegrantes")
@login
def tbodyEquiposIntegrantes():
    if not con.is_connected():
        con.reconnect()
    cursor = con.cursor(dictionary=True)
    
    sql = """
        SELECT 
                ei.idEquipoIntegrante,
                e.nombreEquipo,
                i.nombreIntegrante,
                ei.fechaUnion
        FROM equiposintegrantes ei
        INNER JOIN equipos e 
                ON e.idEquipo = ei.idEquipo
        INNER JOIN integrantes i 
                ON i.idIntegrante = ei.idIntegrante
        ORDER BY ei.idEquipoIntegrante DESC
        LIMIT 10 OFFSET 0
    """
    cursor.execute(sql)
    registros = cursor.fetchall()

    cursor.close()
    return render_template("tbodyEquiposIntegrantes.html", equiposintegrantes=registros)
    
@app.route("/equiposintegrantes/buscar", methods=["GET"])
@login
def buscarEquiposIntegrantes():
    if not con.is_connected():
        con.reconnect()

    args     = request.args
    busqueda = args["busqueda"]
    busqueda = f"%{busqueda}%"

    cursor = con.cursor(dictionary=True)
    sql    = """

    SELECT ei.idEquipoIntegrante, e.nombreEquipo, i.nombreIntegrante
    FROM equiposintegrantes ei
    INNER JOIN equipos e ON e.idEquipo = ei.idEquipo
    INNER JOIN integrantes i ON i.idIntegrante = ei.idIntegrante
    ORDER BY ei.idEquipoIntegrante DESC
    LIMIT 10 OFFSET 0
    
    """
    val = (busqueda,)

    try:
        cursor.execute(sql, val)
        registros = cursor.fetchall()

    except mysql.connector.errors.ProgrammingError as error:
        print(f"Ocurrió un error de programación en MySQL: {error}")
        registros = []

    finally:
        con.close()

    return make_response(jsonify(registros))

@app.route("/equiposintegrantes", methods=["POST"])
@login
def guardarEquiposIntegrantes():
    if not con.is_connected():
        con.reconnect()

    idEquipoIntegrante = request.form["idEquipoIntegrante"]
    idEquipo = request.form["idEquipo"]
    idIntegrante = request.form["idIntegrante"]
    
    cursor = con.cursor()

    if idEquipoIntegrante:
        sql = """
        UPDATE equiposintegrantes
        SET idEquipo = %s,
            idIntegrante = %s,
            fechaUnion = NOW()
        WHERE idEquipoIntegrante = %s
        """
        val = (idEquipo, idIntegrante, idEquipoIntegrante)
    else:
        sql = """
        INSERT INTO equiposintegrantes (idEquipo, idIntegrante, fechaUnion)
        VALUES (%s, %s, NOW())
        """
        val = (idEquipo, idIntegrante)

    cursor.execute(sql, val)
    con.commit()
    con.close()

    pusherEquiposIntegrantes()
    return make_response(jsonify({"mensaje": "EquipoIntegrante guardado"}))

@app.route("/equiposintegrantes/eliminar", methods=["POST"])
@login
def eliminarequiposintegrantes():
    if not con.is_connected():
        con.reconnect()

    id = request.form.get("id")

    cursor = con.cursor(dictionary=True)
    sql = """
    DELETE FROM equiposintegrantes 
    WHERE idEquipoIntegrante = %s
    """
    val = (id,)
    
    cursor.execute(sql, val)
    con.commit()
    con.close()

    pusherEquiposIntegrantes()
    return make_response(jsonify({"mensaje": "Equipo Integrante eliminado"}))

@app.route("/integrantes/lista")
@login
def cargarIntegrantes():
    if not con.is_connected():
        con.reconnect()

    cursor = con.cursor(dictionary=True)
    sql = """
    SELECT idIntegrante , nombreIntegrante 
    FROM integrantes
    ORDER BY nombreIntegrante ASC
    """
    
    cursor.execute(sql)
    registros = cursor.fetchall()
    con.close()
    
    return make_response(jsonify(registros))
    
#////////////////////////////////////////////////////////////////////////////////////////////////////////////////

# Obtener un registro específico de equiposintegrantes (para modificar)
@app.route("/equiposintegrantes/<int:id>", methods=["GET"])
@login
def obtenerEquipoIntegrante(id):

    if not con.is_connected():
        con.reconnect()


        sql = """
        SELECT 
            ei.idEquipoIntegrante,
            ei.idEquipo,
            ei.idIntegrante,
            e.nombreEquipo,
            i.nombreIntegrante
        FROM equiposintegrantes ei
        INNER JOIN equipos e ON e.idEquipo = ei.idEquipo
        INNER JOIN integrantes i ON i.idIntegrante = ei.idIntegrante
        WHERE ei.idEquipoIntegrante = %s
        """
       cursor.execute(sql)
    registros = cursor.fetchall()
    con.close()

        return make_response(jsonify(registros))

    except Exception as e:
        print(f"Error al obtener equipo-integrante: {e}")
        return make_response(jsonify({"error": "Error al obtener el registro"}), 500)

    finally:
        if cursor:
            cursor.close()
        if con and con.is_connected():
            con.close()


if __name__ == "__main__":
    app.run(debug=True, port=5000)







