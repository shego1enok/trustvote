# backend/app.py
import os
import sys
import time
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.auth import register_user, authenticate_user
from backend.models import init_db


def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), '..', 'frontend', 'templates'),
        static_folder=os.path.join(os.path.dirname(__file__), '..', 'frontend', 'static')
    )
    app.secret_key = 'trustvote_secret_key_2025'
    init_db()

    # Внутренняя функция для обновления статуса голосования
    def update_session_status(session_id, cursor):
        cursor.execute("SELECT ended_at, is_active FROM sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()
        if not row or not row['is_active']:
            return False

        try:
            ended_at = datetime.fromisoformat(row['ended_at'])
            if datetime.now() > ended_at:
                cursor.execute("UPDATE sessions SET is_active = 0 WHERE id = ?", (session_id,))
                return True
        except (ValueError, TypeError):
            pass
        return False

    @app.route('/')
    def index():
        if 'user_id' in session:
            return render_template('index.html', username=session.get('username'))
        return redirect(url_for('login'))

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            user_id = authenticate_user(username, password)
            if user_id:
                session['user_id'] = user_id
                session['username'] = username

                # Перенаправление после логина (например, на голосование)
                next_url = request.args.get('next')
                if next_url and next_url.startswith('/'):
                    return redirect(next_url)
                else:
                    return redirect(url_for('index'))
            else:
                flash('Неверный логин или пароль', 'error')
        return render_template('login.html')

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            if len(password) < 4:
                flash('Пароль должен быть не короче 4 символов', 'error')
            elif register_user(username, password):
                flash('Регистрация успешна! Войдите.', 'success')
                return redirect(url_for('login'))
            else:
                flash('Пользователь с таким именем уже существует', 'error')
        return render_template('register.html')

    @app.route('/logout')
    def logout():
        session.clear()
        return redirect(url_for('login'))

    @app.route('/create_vote', methods=['GET', 'POST'])
    def create_vote():
        if 'user_id' not in session:
            return redirect(url_for('login'))

        if request.method == 'POST':
            title = request.form['title'].strip()
            description = request.form.get('description', '').strip()
            candidates_raw = request.form['candidates'].strip()
            duration = int(request.form.get('duration', 24))

            is_anonymous = 'is_anonymous' in request.form
            allow_multiple = 'allow_multiple' in request.form
            show_results_live = 'show_results_live' in request.form

            if not title or not candidates_raw:
                flash('Заполните название и кандидатов', 'error')
                return render_template('create_vote.html')

            candidates = [c.strip() for c in candidates_raw.split('\n') if c.strip()]
            if len(candidates) < 2:
                flash('Добавьте хотя бы двух кандидатов', 'error')
                return render_template('create_vote.html')

            from backend.utils import generate_session_id
            session_id = generate_session_id()

            created_at = datetime.now()
            ended_at = created_at + timedelta(hours=duration)

            from backend.models import get_db_connection
            try:
                conn = get_db_connection()
                cursor = conn.cursor()

                cursor.execute('''
                    INSERT INTO sessions (
                        id, title, description, duration_hours,
                        is_anonymous, allow_multiple, show_results_live,
                        created_at, ended_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (session_id, title, description, duration,
                      int(is_anonymous), int(allow_multiple), int(show_results_live),
                      created_at.isoformat(), ended_at.isoformat()))

                for name in candidates:
                    cursor.execute(
                        "INSERT INTO candidates (session_id, name) VALUES (?, ?)",
                        (session_id, name)
                    )

                conn.commit()
                conn.close()

                return render_template('vote_created.html', session_id=session_id)
            except Exception as e:
                print("Ошибка:", e)
                flash('Ошибка при создании голосования', 'error')
                return render_template('create_vote.html')

        return render_template('create_vote.html')

    @app.route('/vote/<session_id>', methods=['GET', 'POST'])
    def vote_page(session_id):
        from backend.models import get_db_connection
        from backend.utils import generate_user_hash

        # Перенаправление на логин с сохранением точного пути
        if 'user_id' not in session:
            return redirect(url_for('login', next=f'/vote/{session_id}'))  # ← КЛЮЧЕВОЕ ИЗМЕНЕНИЕ

        user_id = session['user_id']

        conn = get_db_connection()
        cursor = conn.cursor()

        update_session_status(session_id, cursor)

        cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        session_data = cursor.fetchone()

        if not session_data or not session_data['is_active']:
            conn.close()
            flash('Голосование не найдено или завершено', 'error')
            return redirect(url_for('index'))

        cursor.execute("SELECT * FROM candidates WHERE session_id = ?", (session_id,))
        candidates = cursor.fetchall()
        conn.close()

        if request.method == 'POST':
            user_hash = generate_user_hash(session_id, user_id)

            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                "SELECT 1 FROM votes WHERE session_id = ? AND user_hash = ?",
                (session_id, user_hash)
            )
            if cursor.fetchone():
                conn.close()
                flash('Вы уже голосовали в этом голосовании!', 'error')
                return redirect(url_for('vote_page', session_id=session_id))

            selected_ids = request.form.getlist('candidate')
            if not selected_ids:
                conn.close()
                flash('Выберите хотя бы одного кандидата', 'error')
                return redirect(url_for('vote_page', session_id=session_id))

            if not session_data['allow_multiple'] and len(selected_ids) > 1:
                conn.close()
                flash('Разрешён только один выбор', 'error')
                return redirect(url_for('vote_page', session_id=session_id))

            cursor.execute(
                "INSERT INTO votes (session_id, user_hash) VALUES (?, ?)",
                (session_id, user_hash)
            )
            vote_id = cursor.lastrowid

            for cid_str in selected_ids:
                cid = int(cid_str)
                cursor.execute(
                    "INSERT INTO vote_choices (vote_id, candidate_id) VALUES (?, ?)",
                    (vote_id, cid)
                )

            conn.commit()
            conn.close()

            from backend.blockchain import Blockchain
            blockchain = Blockchain(session_id)
            vote_data = {
                "vote_id": vote_id,
                "session_id": session_id,
                "timestamp": time.time(),
                "candidate_ids": selected_ids
            }
            blockchain.add_vote(vote_data)

            flash('✅ Ваш голос учтён и защищён блокчейном!', 'success')
            return redirect(url_for('index'))

        return render_template('vote_page.html', session=session_data, candidates=candidates)

    @app.route('/results')
    def results_list():
        if 'user_id' not in session:
            return redirect(url_for('login'))

        from backend.models import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sessions ORDER BY created_at DESC")
        sessions = cursor.fetchall()
        conn.close()

        return render_template('results_list.html', sessions=sessions)

    @app.route('/results/<session_id>')
    def results_page(session_id):
        from backend.models import get_db_connection
        from backend.blockchain import Blockchain

        conn = get_db_connection()
        cursor = conn.cursor()

        update_session_status(session_id, cursor)

        cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        session_data = cursor.fetchone()
        if not session:  # исправлено
            conn.close()
            flash('Голосование не найдено', 'error')
            return redirect(url_for('index'))

        if not session_data['show_results_live'] and session_data['is_active']:
            conn.close()
            flash('Результаты будут доступны после завершения голосования', 'error')
            return redirect(url_for('index'))

        cursor.execute("SELECT * FROM candidates WHERE session_id = ?", (session_id,))
        candidates = {row['id']: row['name'] for row in cursor.fetchall()}

        cursor.execute("""
            SELECT vc.candidate_id, COUNT(*) as vote_count
            FROM vote_choices vc
            JOIN votes v ON vc.vote_id = v.id
            WHERE v.session_id = ?
            GROUP BY vc.candidate_id
        """, (session_id,))
        vote_counts = {row['candidate_id']: row['vote_count'] for row in cursor.fetchall()}

        cursor.execute("SELECT COUNT(*) as total FROM votes WHERE session_id = ?", (session_id,))
        total_votes = cursor.fetchone()['total']

        conn.close()

        blockchain = Blockchain(session_id)
        is_valid = blockchain.is_chain_valid()

        results = []
        for cid, name in candidates.items():
            votes_for = vote_counts.get(cid, 0)
            percent = (votes_for / total_votes * 100) if total_votes > 0 else 0
            results.append({
                'name': name,
                'votes': votes_for,
                'percent': percent
            })
        results.sort(key=lambda x: x['votes'], reverse=True)

        return render_template(
            'results.html',
            session=session_data,
            results=results,
            total_votes=total_votes,
            block_count=len(blockchain.chain),
            is_valid=is_valid
        )

    @app.route('/api/results/<session_id>/journal')
    def get_journal(session_id):
        from backend.models import get_db_connection

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM sessions WHERE id = ?", (session_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({"error": "Голосование не найдено"}), 404

        cursor.execute("SELECT id, name FROM candidates WHERE session_id = ?", (session_id,))
        candidates = {row['id']: row['name'] for row in cursor.fetchall()}

        cursor.execute("""
            SELECT v.id, v.user_hash, v.created_at, vc.candidate_id
            FROM votes v
            JOIN vote_choices vc ON v.id = vc.vote_id
            WHERE v.session_id = ?
            ORDER BY v.created_at
        """, (session_id,))
        votes = cursor.fetchall()
        conn.close()

        journal = []
        for row in votes:
            journal.append({
                "vote_id": row['id'],
                "user_hash": row['user_hash'],
                "candidate": candidates.get(row['candidate_id'], "—"),
                "created_at": row['created_at']
            })

        return jsonify({"journal": journal})

    @app.route('/api/health')
    def health():
        return jsonify({"status": "ok"})

    @app.route('/api/stats')
    def get_stats():
        from backend.models import get_db_connection

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as total FROM blocks")
        blocks_count = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) as total FROM sessions WHERE is_active = 1")
        active_sessions = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) as total FROM votes")
        total_votes = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(DISTINCT user_hash) as total FROM votes")
        participants = cursor.fetchone()['total']

        conn.close()

        return jsonify({
            "blocks": blocks_count,
            "active_sessions": active_sessions,
            "total_votes": total_votes,
            "participants": participants
        })

    @app.route('/api/results/<session_id>/pdf')
    def export_pdf(session_id):
        from backend.models import get_db_connection
        from fpdf import FPDF
        from io import BytesIO
        import os

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        session_data = cursor.fetchone()
        if not session:
            conn.close()
            return "Голосование не найдено", 404

        cursor.execute("SELECT * FROM candidates WHERE session_id = ?", (session_id,))
        candidates = {row['id']: row['name'] for row in cursor.fetchall()}

        cursor.execute("""
            SELECT vc.candidate_id, COUNT(*) as vote_count
            FROM vote_choices vc
            JOIN votes v ON vc.vote_id = v.id
            WHERE v.session_id = ?
            GROUP BY vc.candidate_id
        """, (session_id,))
        vote_counts = {row['candidate_id']: row['vote_count'] for row in cursor.fetchall()}

        cursor.execute("SELECT COUNT(*) as total FROM votes WHERE session_id = ?", (session_id,))
        total_votes = cursor.fetchone()['total']

        conn.close()

        results = []
        for cid, name in candidates.items():
            votes_for = vote_counts.get(cid, 0)
            percent = (votes_for / total_votes * 100) if total_votes > 0 else 0
            results.append([name, votes_for, f"{percent:.1f}%"])

        results.sort(key=lambda x: x[1], reverse=True)

        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

        font_dir = os.path.join(os.path.dirname(__file__), '..', 'fonts')
        regular_font = os.path.join(font_dir, 'DejaVuSans.ttf')
        bold_font = os.path.join(font_dir, 'DejaVuSans-Bold.ttf')

        pdf.add_font("DejaVu", "", regular_font, uni=True)
        pdf.add_font("DejaVu", "B", bold_font, uni=True)

        pdf.set_font("DejaVu", "B", 16)
        pdf.cell(0, 10, "TrustVote — Отчёт о голосовании", 0, 1, "C")
        pdf.ln(10)

        pdf.set_font("DejaVu", "", 12)
        pdf.cell(0, 8, f"Название: {session_data['title']}", 0, 1)
        if session_data['description']:
            pdf.cell(0, 8, f"Описание: {session_data['description']}", 0, 1)
        pdf.cell(0, 8, f"Дата создания: {session_data['created_at']}", 0, 1)
        pdf.cell(0, 8, f"Всего голосов: {total_votes}", 0, 1)
        pdf.ln(10)

        if results:
            pdf.set_font("DejaVu", "B", 12)
            pdf.cell(80, 10, "Кандидат", 1, 0, "C")
            pdf.cell(40, 10, "Голоса", 1, 0, "C")
            pdf.cell(40, 10, "Процент", 1, 1, "C")

            pdf.set_font("DejaVu", "", 12)
            for name, votes, percent in results:
                pdf.cell(80, 10, name, 1, 0, "L")
                pdf.cell(40, 10, str(votes), 1, 0, "C")
                pdf.cell(40, 10, percent, 1, 1, "C")
        else:
            pdf.cell(0, 10, "Нет голосов для отображения.", 0, 1, "C")

        pdf.ln(15)
        pdf.set_font("DejaVu", "", 10)
        pdf.cell(0, 10, "✅ Отчёт сгенерирован системой TrustVote", 0, 1, "C")

        buffer = BytesIO()
        pdf.output(buffer)
        pdf_bytes = buffer.getvalue()
        buffer.close()

        from flask import Response
        return Response(
            pdf_bytes,
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename=trustvote_{session_id}_report.pdf'
            }
        )

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='127.0.0.1', port=5000, debug=True)