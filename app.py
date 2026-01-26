import os
import json
import sqlite3
import frontmatter  # Requiere: pip install python-frontmatter
import markdown     # Requiere: pip install markdown
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

# ========== CONFIGURACIÓN ==========
app = Flask(__name__)
app.config['SECRET_KEY'] = 'rpg-master-secret'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB

# Directorios de contenido
MONSTERS_DIR = 'monsters' 
SPELLS_DIR = 'spells'
RULES_DIR = 'rules'

# Crear carpetas necesarias
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'images'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'videos'), exist_ok=True)
os.makedirs(MONSTERS_DIR, exist_ok=True) 
os.makedirs(SPELLS_DIR, exist_ok=True)
os.makedirs(RULES_DIR, exist_ok=True)

# Inicializar archivos JSON de estado
if not os.path.exists('screen_command.json'):
    with open('screen_command.json', 'w') as f:
        json.dump({'type': 'initiative', 'data': None, 'timestamp': datetime.now().isoformat()}, f)

if not os.path.exists('whiteboard_state.json'):
    with open('whiteboard_state.json', 'w') as f:
        json.dump({'state': None, 'timestamp': datetime.now().isoformat()}, f)

# ========== BASE DE DATOS ==========
def init_db():
    conn = sqlite3.connect('rpg.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS characters
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  initiative INTEGER NOT NULL,
                  hp INTEGER,
                  max_hp INTEGER,
                  type TEXT DEFAULT 'player',
                  is_active INTEGER DEFAULT 1,
                  monster_slug TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS game_state
                 (id INTEGER PRIMARY KEY,
                  current_turn INTEGER DEFAULT 0,
                  round_number INTEGER DEFAULT 1,
                  last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    c.execute('INSERT OR IGNORE INTO game_state (id) VALUES (1)')
    conn.commit()
    conn.close()

init_db()

# ========== FUNCIONES DE AYUDA (DB) ==========
def get_db():
    conn = sqlite3.connect('rpg.db')
    conn.row_factory = sqlite3.Row 
    return conn

def get_characters():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM characters WHERE is_active = 1 ORDER BY initiative DESC, name') 
    characters = c.fetchall()
    conn.close()
    return characters

def get_game_state():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM game_state WHERE id = 1')
    state = c.fetchone()
    conn.close()
    return state

def save_screen_command(command_type, data=None):
    command = {
        'type': command_type,
        'data': data,
        'timestamp': datetime.now().isoformat()
    }
    with open('screen_command.json', 'w') as f:
        json.dump(command, f)
    return command

def save_whiteboard_state_file(state_data):
    state = {
        'state': state_data,
        'timestamp': datetime.now().isoformat()
    }
    with open('whiteboard_state.json', 'w') as f:
        json.dump(state, f)
    return state

# ========== LÓGICA DE CONTENIDO (GENÉRICA) ==========
def cargar_contenido_markdown(directorio):
    """Carga archivos .md de un directorio y devuelve lista de metadatos."""
    lista_items = []
    if not os.path.exists(directorio):
        return lista_items

    for filename in os.listdir(directorio):
        if filename.endswith('.md'):
            filepath = os.path.join(directorio, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    post = frontmatter.load(f)
                item_data = post.metadata
                item_data['slug'] = filename.replace('.md', '') 
                
                # Asegurar campo nombre/título
                if 'nombre' not in item_data and 'title' in item_data:
                    item_data['nombre'] = item_data['title']
                if 'nombre' not in item_data:
                    item_data['nombre'] = item_data['slug']
                    
                lista_items.append(item_data)
            except Exception as e:
                print(f"Error leyendo {filename} en {directorio}: {e}")
    
    return sorted(lista_items, key=lambda x: x.get('nombre', '').lower())

def get_markdown_detail(directorio, slug):
    """Obtiene el contenido HTML y metadatos de un slug específico."""
    filepath = os.path.join(directorio, f'{slug}.md')
    if not os.path.exists(filepath):
        return None, None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            post = frontmatter.load(f)
        contenido_html = markdown.markdown(post.content, extensions=['tables'])
        return post.metadata, contenido_html
    except Exception:
        return None, None

# ========== RUTAS DE VISTAS (HTML) ==========
@app.route('/')
def index(): return master()

@app.route('/master')
def master():
    characters_data = get_characters()
    game_state = get_game_state()
    
    # Cargar los 3 tipos de contenido
    monsters = cargar_contenido_markdown(MONSTERS_DIR)
    spells = cargar_contenido_markdown(SPELLS_DIR)
    rules = cargar_contenido_markdown(RULES_DIR)
    
    return render_template('master.html', 
                           characters=characters_data, 
                           current_turn=game_state['current_turn'], 
                           grimorio_monsters=monsters,
                           grimorio_spells=spells,
                           grimorio_rules=rules)

@app.route('/player')
def player(): return render_template('player.html')

@app.route('/player/screen')
def player_screen(): return render_template('player.html', fullscreen=True)

# Ruta unificada para obtener detalles (AJAX)
@app.route('/content/<ctype>/<slug>')
def get_content_detail(ctype, slug):
    directory = MONSTERS_DIR
    if ctype == 'spell': directory = SPELLS_DIR
    elif ctype == 'rule': directory = RULES_DIR
    
    metadata, html = get_markdown_detail(directory, slug)
    if not metadata:
        return '<div class="error">No encontrado</div>', 404
        
    # Renderizamos una plantilla parcial o devolvemos HTML directo
    # Asumimos que existe monstruo_detalle.html, podemos reutilizarlo para todos
    return render_template('monstruo_detalle.html', metadata=metadata, contenido=html, type=ctype)

# ========== API: PIZARRA ==========
@app.route('/api/whiteboard/save', methods=['POST'])
def api_save_whiteboard():
    data = request.json
    state_json = data.get('state')
    if not state_json: return jsonify({'success': False}), 400
    save_whiteboard_state_file(state_json)
    return jsonify({'success': True})

@app.route('/api/whiteboard/load', methods=['GET'])
def api_load_whiteboard():
    try:
        with open('whiteboard_state.json', 'r') as f:
            state = json.load(f)
        return jsonify(state)
    except:
        return jsonify({'state': None})

# ========== API: PERSONAJES ==========
@app.route('/api/characters', methods=['GET'])
def api_get_characters():
    characters = get_characters()
    game_state = get_game_state()
    characters_list = []
    for i, char in enumerate(characters):
        char_dict = dict(char)
        portrait_path = None
        # Buscar retrato si es monstruo
        if char_dict.get('type') == 'monster' and char_dict.get('monster_slug'):
            meta, _ = get_markdown_detail(MONSTERS_DIR, char_dict['monster_slug'])
            if meta: portrait_path = meta.get('portrait_path')

        characters_list.append({
            'id': char['id'],
            'name': char['name'],
            'initiative': char['initiative'],
            'hp': char['hp'],
            'max_hp': char['max_hp'],
            'type': char['type'],
            'order': i + 1,
            'isCurrent': (i == game_state['current_turn']),
            'portrait_path': portrait_path
        })
    return jsonify({
        'success': True,
        'characters': characters_list,
        'current_turn': game_state['current_turn'],
        'round_number': game_state['round_number']
    })

@app.route('/api/characters', methods=['POST'])
def api_add_character():
    data = request.json
    if not data.get('name'): return jsonify({'success': False}), 400
    conn = get_db()
    c = conn.cursor()
    c.execute('''INSERT INTO characters (name, initiative, hp, max_hp, type, monster_slug) VALUES (?, ?, ?, ?, ?, ?)''',
              (data['name'], int(data.get('initiative', 0)), data.get('hp'), data.get('max_hp'), data.get('type', 'player'), data.get('slug')))
    conn.commit()
    conn.close()
    save_screen_command('initiative')
    return jsonify({'success': True})

@app.route('/api/characters/<int:char_id>', methods=['DELETE'])
def api_delete_character(char_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE characters SET is_active = 0 WHERE id = ?', (char_id,))
    conn.commit()
    conn.close()
    save_screen_command('initiative')
    return jsonify({'success': True})

@app.route('/api/characters/<int:char_id>/hp', methods=['PUT'])
def api_update_hp(char_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE characters SET hp = ? WHERE id = ?', (request.json.get('hp'), char_id))
    conn.commit()
    conn.close()
    save_screen_command('initiative')
    return jsonify({'success': True})

# ========== API: JUEGO ==========
@app.route('/api/game/next-turn', methods=['POST'])
def api_next_turn():
    conn = get_db()
    c = conn.cursor()
    state = get_game_state()
    c.execute("SELECT COUNT(*) FROM characters WHERE is_active = 1")
    total = c.fetchone()[0]
    if total == 0: 
        conn.close()
        return jsonify({'success': False})
    new_turn = (state['current_turn'] + 1) % total
    round_number = state['round_number'] + 1 if new_turn == 0 else state['round_number']
    c.execute('UPDATE game_state SET current_turn = ?, round_number = ?, last_updated = CURRENT_TIMESTAMP WHERE id = 1', (new_turn, round_number))
    conn.commit()
    conn.close()
    save_screen_command('initiative')
    return jsonify({'success': True})

@app.route('/api/game/prev-turn', methods=['POST'])
def api_prev_turn():
    conn = get_db()
    c = conn.cursor()
    state = get_game_state()
    c.execute("SELECT COUNT(*) FROM characters WHERE is_active = 1")
    total = c.fetchone()[0]
    if total == 0: 
        conn.close()
        return jsonify({'success': False})
    new_turn = (state['current_turn'] - 1 + total) % total
    round_number = state['round_number'] - 1 if (state['current_turn'] == 0 and new_turn == (total - 1) and state['round_number'] > 1) else state['round_number']
    c.execute('UPDATE game_state SET current_turn = ?, round_number = ?, last_updated = CURRENT_TIMESTAMP WHERE id = 1', (new_turn, round_number))
    conn.commit()
    conn.close()
    save_screen_command('initiative')
    return jsonify({'success': True})

@app.route('/api/game/reset', methods=['POST'])
def api_reset_game():
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE characters SET is_active = 0')
    c.execute('UPDATE game_state SET current_turn = 0, round_number = 1 WHERE id = 1')
    conn.commit()
    conn.close()
    save_screen_command('clear')
    return jsonify({'success': True})

# ========== API: MEDIA Y PANTALLA ==========
@app.route('/api/media/upload', methods=['POST'])
def api_upload_media():
    if 'file' not in request.files: return jsonify({'success': False}), 400
    file = request.files['file']
    if file.filename == '': return jsonify({'success': False}), 400

    # Detectar tipo por parámetro o extensión
    media_type = request.args.get('type', 'auto') 
    filename = secure_filename(file.filename)
    ext = filename.lower()
    
    # Lógica de carpetas (Audio, Video, Imagen)
    if media_type == 'audio' or ext.endswith(('.mp3', '.wav', '.ogg')):
        folder_name = 'audio'
    elif ext.endswith(('.mp4', '.webm', '.mov')):
        folder_name = 'videos'
    else:
        folder_name = 'images'

    target_folder = os.path.join(app.config['UPLOAD_FOLDER'], folder_name)
    os.makedirs(target_folder, exist_ok=True)
    file.save(os.path.join(target_folder, filename))
    
    return jsonify({'success': True, 'url': f'/static/uploads/{folder_name}/{filename}', 'filename': filename})

# ==========================================
# FIN DEL ARREGLO
# ==========================================
@app.route('/api/screen/command', methods=['POST'])
def api_set_command():
    save_screen_command(request.json.get('type'), request.json.get('data'))
    return jsonify({'success': True})

# NUEVO: Endpoint para mostrar una tarjeta de información (HTML)
@app.route('/api/screen/show-card', methods=['POST'])
def api_show_card():
    # Recibe título y html
    data = request.json
    save_screen_command('info_card', data)
    return jsonify({'success': True})

@app.route('/api/screen/youtube-control', methods=['POST'])
def api_youtube_control():
    save_screen_command('youtube_control', {'action': request.json.get('action')})
    return jsonify({'success': True})

@app.route('/api/screen/show-image', methods=['POST'])
def api_show_image():
    save_screen_command('image', {'url': request.json.get('url')})
    return jsonify({'success': True})

@app.route('/api/screen/show-video', methods=['POST'])
def api_show_video():
    save_screen_command('video', {'url': request.json.get('url'), 'autoplay': True})
    return jsonify({'success': True})

@app.route('/api/screen/show-youtube', methods=['POST'])
def api_show_youtube():
    save_screen_command('youtube', {'video_id': request.json.get('video_id'), 'autoplay': True, 'muted': False})
    return jsonify({'success': True})

@app.route('/api/screen/show-initiative', methods=['POST'])
def api_show_initiative():
    save_screen_command('initiative')
    return jsonify({'success': True})

@app.route('/api/screen/clear', methods=['POST'])
def api_clear_screen():
    save_screen_command('clear')
    return jsonify({'success': True})

@app.route('/api/screen/blackout', methods=['POST'])
def api_blackout_screen():
    save_screen_command('blackout')
    return jsonify({'success': True})

# RUTA PARA JUGADORES (LECTURA)
@app.route('/api/screen/command', methods=['GET'])
def api_get_command():
    try:
        with open('screen_command.json', 'r') as f: return jsonify(json.load(f))
    except: return jsonify({'type': 'initiative'})

@app.route('/static/uploads/<path:filename>')
def serve_uploads(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
# ... (Resto del código igual) ...

# NUEVO: Endpoint para renderizar Markdown crudo a HTML bajo demanda
@app.route('/api/render-markdown-text', methods=['POST'])
def api_render_markdown_text():
    data = request.json
    text = data.get('text', '')
    # Usamos las mismas extensiones que en el resto de la app
    html_content = markdown.markdown(text, extensions=['tables'])
    return jsonify({'success': True, 'html': html_content})

@app.route('/api/screen/toggle-grid', methods=['POST'])
def api_toggle_grid():
    data = request.json
    # Guardamos el comando para que la pantalla del jugador lo lea
    # Usamos la estructura que ya tiene tu app para comandos de pantalla
    save_screen_command('toggle-grid', {'show': data.get('show', False)})
    return jsonify({'success': True})
# ==========================================
# PEGAR ESTO AQUÍ (ARREGLO DE AUDIO)
# ==========================================

@app.route('/api/audio/list', methods=['GET'])
def list_audios():
    audio_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'audio')
    # Nos aseguramos de que la carpeta exista
    os.makedirs(audio_dir, exist_ok=True)
    try:
        files = [f for f in os.listdir(audio_dir) if f.lower().endswith(('.mp3', '.wav', '.ogg'))]
        return jsonify(files)
    except: return jsonify([])

if __name__ == '__main__':
    # Usamos rpg.db como indicaste
    if not os.path.exists('rpg.db'):
        conn = sqlite3.connect('rpg.db')
        conn.execute('CREATE TABLE characters (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, initiative INTEGER, hp INTEGER, max_hp INTEGER, type TEXT, portrait_path TEXT)')
        conn.close()
    
    print("🚀 Servidor RPG Master iniciado en http://127.0.0.1:5000")
    app.run(debug=True, port=5000)