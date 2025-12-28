# backend/blockchain.py
import hashlib
import time
import json
from typing import List, Dict
from backend.models import get_db_connection

class Block:
    def __init__(self, index: int, previous_hash: str, data: List[Dict], difficulty: int = 2, nonce: int = 0):
        self.index = index
        self.timestamp = time.time()
        self.previous_hash = previous_hash
        self.data = data
        self.nonce = nonce
        self.difficulty = difficulty
        self.hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        block_string = json.dumps({
            "index": self.index,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "data": self.data,
            "nonce": self.nonce
        }, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def mine_block(self) -> str:
        target = "0" * self.difficulty
        while True:
            hash_result = self.calculate_hash()
            if hash_result[:self.difficulty] == target:
                self.hash = hash_result
                return hash_result
            self.nonce += 1


class Blockchain:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.chain = []
        self.pending_votes = []
        self.difficulty = 2
        self.block_capacity = 5
        self._load_from_db()

    def _load_from_db(self):
        """Загружает цепочку из базы данных"""
        conn = get_db_connection()
        cursor = conn.cursor()

        # Загружаем блоки
        cursor.execute(
            "SELECT * FROM blocks WHERE session_id = ? ORDER BY block_index",
            (self.session_id,)
        )
        blocks = cursor.fetchall()
        for block_row in blocks:
            data = json.loads(block_row['data'])
            block = Block(
                index=block_row['block_index'],
                previous_hash=block_row['previous_hash'],
                data=data,
                difficulty=self.difficulty,
                nonce=block_row['nonce']
            )
            block.timestamp = block_row['timestamp']
            block.hash = block_row['current_hash']
            self.chain.append(block)

        conn.close()

    def add_vote(self, vote_data: Dict):
        """Добавляет голос в очередь и сохраняет в БД сразу"""
        self.pending_votes.append(vote_data)

        if len(self.pending_votes) >= self.block_capacity:
            self.mine_pending_votes()

    def is_chain_valid(self) -> bool:
        """Проверяет целостность цепочки"""
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]

            # Проверяем хэш
            if current.hash != current.calculate_hash():
                return False

            # Проверяем связь
            if current.previous_hash != previous.hash:
                return False

        return True

    def mine_pending_votes(self):
        if not self.pending_votes:
            return

        last_hash = self.chain[-1].hash if self.chain else "0"
        block = Block(
            index=len(self.chain),
            previous_hash=last_hash,
            data=self.pending_votes.copy(),
            difficulty=self.difficulty
        )
        block.mine_block()  # майнинг

        # Сохраняем блок в БД
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO blocks (
                session_id, block_index, previous_hash, current_hash, nonce, data
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            self.session_id,
            block.index,
            block.previous_hash,
            block.hash,
            block.nonce,
            json.dumps(block.data)
        ))
        block_id = cursor.lastrowid

        # Обновляем block_id для всех голосов в этом блоке
        # В реальной системе нужно связать по user_hash и session_id
        # Пока упростим: обновим все голоса без block_id за последние 5 секунд
        cursor.execute('''
            UPDATE votes 
            SET block_id = ?
            WHERE session_id = ? AND block_id IS NULL
            AND created_at > datetime('now', '-5 seconds')
        ''', (block_id, self.session_id))

        conn.commit()
        conn.close()

        self.chain.append(block)
        self.pending_votes.clear()