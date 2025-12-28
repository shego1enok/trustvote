// script.js — основной JavaScript для TrustVote

// Функция обновления статистики
/*
function updateStats() {
    const statBlocks = document.getElementById('stat-blocks');
    const statSessions = document.getElementById('stat-sessions');
    const statVotes = document.getElementById('stat-votes');
    const statParticipants = document.getElementById('stat-participants');

    if (statBlocks && statSessions && statVotes && statParticipants) {
        fetch('/api/stats')
            .then(response => response.json())
            .then(data => {
                statBlocks.querySelector('h4').textContent = data.blocks;
                statSessions.querySelector('h4').textContent = data.active_sessions;
                statVotes.querySelector('h4').textContent = data.total_votes;
                statParticipants.querySelector('h4').textContent = data.participants;
            })
            .catch(error => {
                console.error('Ошибка загрузки статистики:', error);
            });
    }
}

// Генерация QR-кода (офлайн-версия)
function generateQRCode(sessionId) {
    if (!sessionId) return;

    const baseUrl = window.location.origin;
    const voteUrl = `${baseUrl}/vote/${sessionId}`;

    // Показываем URL
    const qrUrlEl = document.getElementById('qrUrl');
    if (qrUrlEl) qrUrlEl.textContent = voteUrl;

    // Создаём canvas вместо внешней библиотеки (работает в EXE)
    const qrContainer = document.getElementById('qrcode');
    qrContainer.innerHTML = '<canvas id="qrCanvas" width="200" height="200"></canvas>';
    const canvas = document.getElementById('qrCanvas');
    const ctx = canvas.getContext('2d');

    // Фон
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, 200, 200);

    // Простой "QR" — текст с кодом
    ctx.fillStyle = '#000000';
    ctx.font = 'bold 16px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('Голосование', 100, 80);
    ctx.font = '14px monospace';
    ctx.fillText(sessionId.substring(0, 12), 100, 110);
    ctx.fillText('...', 100, 130);

    // Показываем блок
    document.getElementById('qrContainer').style.display = 'block';

    // Добавляем копирование при клике на URL
    qrUrlEl.addEventListener('click', () => {
        navigator.clipboard.writeText(voteUrl).then(() => {
            alert('✅ Ссылка скопирована!');
        }).catch(err => {
            console.error('Не удалось скопировать:', err);
            alert('❌ Не удалось скопировать. Скопируйте вручную.');
        });
    });
}

document.addEventListener('DOMContentLoaded', function () {
    // === 1. Статистика на главной ===
    updateStats();
    const statsInterval = setInterval(updateStats, 30000);
    window.addEventListener('beforeunload', () => clearInterval(statsInterval));

    // === 2. Журнал голосов ===
    const toggleBtn = document.getElementById('toggleJournal');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', function () {
            const sessionId = this.getAttribute('data-session-id');
            const journalContainer = document.getElementById('journalContainer');
            const journalContent = document.getElementById('journalContent');

            if (!journalContainer) return;

            if (journalContainer.style.display === 'none' || journalContainer.style.display === '') {
                fetch(`/api/results/${sessionId}/journal`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.journal && data.journal.length > 0) {
                            let html = '<div class="journal-table">';
                            html += '<div class="journal-row header">';
                            html += '<div>Голос ID</div>';
                            html += '<div>Анонимный хэш</div>';
                            html += '<div>Кандидат</div>';
                            html += '<div>Время</div>';
                            html += '</div>';

                            data.journal.forEach(entry => {
                                html += '<div class="journal-row">';
                                html += `<div>${entry.vote_id}</div>`;
                                html += `<div><code>${entry.user_hash.substring(0, 12)}...</code></div>`;
                                html += `<div>${entry.candidate}</div>`;
                                html += `<div>${entry.created_at.replace(' ', '<br>')}</div>`;
                                html += '</div>';
                            });
                            html += '</div>';
                            journalContent.innerHTML = html;
                        } else {
                            journalContent.innerHTML = '<p>Нет данных для отображения.</p>';
                        }
                        journalContainer.style.display = 'block';
                        toggleBtn.textContent = 'Скрыть журнал';
                    })
                    .catch(error => {
                        journalContent.innerHTML = `<p style="color: red;">Ошибка: ${error.message}</p>`;
                        journalContainer.style.display = 'block';
                    });
            } else {
                journalContainer.style.display = 'none';
                toggleBtn.textContent = 'Показать журнал голосов';
            }
        });
    }

    // === 3. QR-код ===
    const successAlert = document.querySelector('.alert-success');
    if (successAlert) {
        // Получаем чистый текст без HTML
        const text = successAlert.textContent || successAlert.innerText;
        const match = text.match(/([A-Za-z0-9]{8,})/);
        if (match) {
            setTimeout(() => generateQRCode(match[1]), 500);
        }
    }

    // === 4. Кликабельные ссылки в инструкции ===
    const instructionBox = document.querySelector('.instruction-box');
    if (instructionBox) {
        const links = instructionBox.querySelectorAll('code');
        links.forEach(code => {
            code.style.cursor = 'pointer';
            code.style.backgroundColor = '#d0eaff';
            code.style.padding = '2px 6px';
            code.style.borderRadius = '4px';
            code.style.fontFamily = 'monospace';
            code.addEventListener('click', () => {
                const text = code.textContent;
                navigator.clipboard.writeText(text).then(() => {
                    alert(`✅ "${text}" скопировано!`);
                }).catch(err => {
                    console.error('Не удалось скопировать:', err);
                    alert('❌ Не удалось скопировать. Выделите и скопируйте вручную.');
                });
            });
        });
    }
});


// === QR-код на странице успеха ===
document.addEventListener('DOMContentLoaded', () => {
    // Ищем код сессии в URL (если передан)
    const urlParams = new URLSearchParams(window.location.search);
    const sessionId = urlParams.get('session_id');

    if (sessionId) {
        generateQRCode(sessionId);
    }

    // Или если есть элемент с кодом
    const codeElement = document.querySelector('code');
    if (codeElement && !sessionId) {
        const text = codeElement.textContent || codeElement.innerText;
        const match = text.match(/([A-Za-z0-9]{8,})/);
        if (match) {
            generateQRCode(match[1]);
        }
    }
});

function generateQRCode(sessionId) {
    if (!sessionId) return;

    const baseUrl = window.location.origin;
    const voteUrl = `${baseUrl}/vote/${sessionId}`;

    // Показываем URL
    const qrUrlEl = document.getElementById('qrUrl');
    if (qrUrlEl) qrUrlEl.textContent = voteUrl;

    // Создаём canvas вместо внешней библиотеки
    const qrContainer = document.getElementById('qrcode');
    qrContainer.innerHTML = '<canvas id="qrCanvas" width="200" height="200"></canvas>';
    const canvas = document.getElementById('qrCanvas');
    const ctx = canvas.getContext('2d');

    // Фон
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, 200, 200);

    // Простой "QR" — текст с кодом
    ctx.fillStyle = '#000000';
    ctx.font = 'bold 16px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('Голосование', 100, 80);
    ctx.font = '14px monospace';
    ctx.fillText(sessionId.substring(0, 12), 100, 110);
    ctx.fillText('...', 100, 130);

    // Показываем блок
    document.getElementById('qrContainer').style.display = 'block';

    // Копирование при клике на URL
    qrUrlEl.addEventListener('click', () => {
        navigator.clipboard.writeText(voteUrl).then(() => {
            alert('✅ Ссылка скопирована!');
        }).catch(err => {
            console.error('Не удалось скопировать:', err);
            alert('❌ Не удалось скопировать. Скопируйте вручную.');
        });
    });

    // Копирование кода сессии
    const codeElement = document.querySelector('code');
    if (codeElement) {
        codeElement.style.cursor = 'pointer';
        codeElement.style.backgroundColor = '#d0eaff';
        codeElement.style.padding = '2px 6px';
        codeElement.style.borderRadius = '4px';
        codeElement.style.fontFamily = 'monospace';
        codeElement.addEventListener('click', () => {
            navigator.clipboard.writeText(sessionId).then(() => {
                alert(`✅ "${sessionId}" скопировано!`);
            }).catch(err => {
                console.error('Не удалось скопировать:', err);
                alert('❌ Не удалось скопировать. Выделите и скопируйте вручную.');
            });
        });
    }
}*/

// script.js — TrustVote (минимальная стабильная версия)

// === Статистика ===
function updateStats() {
    const cards = {
        blocks: document.getElementById('stat-blocks'),
        sessions: document.getElementById('stat-sessions'),
        votes: document.getElementById('stat-votes'),
        participants: document.getElementById('stat-participants')
    };

    if (Object.values(cards).some(el => el)) {
        fetch('/api/stats')
            .then(r => r.json())
            .then(data => {
                if (cards.blocks) cards.blocks.querySelector('h4').textContent = data.blocks;
                if (cards.sessions) cards.sessions.querySelector('h4').textContent = data.active_sessions;
                if (cards.votes) cards.votes.querySelector('h4').textContent = data.total_votes;
                if (cards.participants) cards.participants.querySelector('h4').textContent = data.participants;
            })
            .catch(e => console.error('Статистика: ошибка', e));
    }
}

// === Журнал голосов ===
function initJournalToggle() {
    const btn = document.getElementById('toggleJournal');
    if (!btn) return;

    btn.addEventListener('click', () => {
        const id = btn.getAttribute('data-session-id');
        const container = document.getElementById('journalContainer');
        const content = document.getElementById('journalContent');

        if (!container || !content) return;

        if (container.style.display === 'none') {
            fetch(`/api/results/${id}/journal`)
                .then(r => r.json())
                .then(data => {
                    if (data.journal?.length) {
                        let html = '<div class="journal-table"><div class="journal-row header">';
                        html += '<div>Голос ID</div><div>Хэш</div><div>Кандидат</div><div>Время</div></div>';
                        data.journal.forEach(e => {
                            html += `<div class="journal-row">
                                <div>${e.vote_id}</div>
                                <div><code>${e.user_hash.substring(0,12)}...</code></div>
                                <div>${e.candidate}</div>
                                <div>${e.created_at.replace(' ', '<br>')}</div>
                            </div>`;
                        });
                        html += '</div>';
                        content.innerHTML = html;
                    } else {
                        content.innerHTML = '<p>Нет данных.</p>';
                    }
                    container.style.display = 'block';
                    btn.textContent = 'Скрыть журнал';
                })
                .catch(e => {
                    content.innerHTML = `<p style="color:red">Ошибка: ${e.message}</p>`;
                    container.style.display = 'block';
                });
        } else {
            container.style.display = 'none';
            btn.textContent = 'Показать журнал голосов';
        }
    });
}

// === Инициализация ===
document.addEventListener('DOMContentLoaded', () => {
    updateStats();
    setInterval(updateStats, 30000);
    initJournalToggle();
});