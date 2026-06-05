#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
笔记管理模块 - 存储交易纪律、狼大策略和短期安排
"""

import logging
from datetime import datetime
from .database import DatabaseManager

logger = logging.getLogger(__name__)


class NoteType:
    """笔记类型枚举"""
    DISCIPLINE = "discipline"          # 交易纪律
    STRATEGY = "strategy"              # 狼大策略
    SHORT_TERM = "short_term"          # 短期安排（今日）


class NotesManager:
    """笔记管理器"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self._init_notes_table()
    
    def _init_notes_table(self):
        """初始化笔记表"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    note_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("笔记表初始化完成")
        except Exception as e:
            logger.error(f"笔记表初始化失败: {e}")
    
    def add_note(self, note_type, title, content):
        """添加笔记"""
        try:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            conn = self.db._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO notes (note_type, title, content, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (note_type, title, content, now, now))
            
            note_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logger.info(f"添加笔记成功: {title}")
            return note_id
        except Exception as e:
            logger.error(f"添加笔记失败: {e}")
            return None
    
    def update_note(self, note_id, title, content):
        """更新笔记"""
        try:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            conn = self.db._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE notes SET title=?, content=?, updated_at=? WHERE id=?
            ''', (title, content, now, note_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"更新笔记成功: {note_id}")
            return True
        except Exception as e:
            logger.error(f"更新笔记失败: {e}")
            return False
    
    def delete_note(self, note_id):
        """删除笔记"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM notes WHERE id = ?', (note_id,))
            conn.commit()
            conn.close()
            
            logger.info(f"删除笔记成功: {note_id}")
            return True
        except Exception as e:
            logger.error(f"删除笔记失败: {e}")
            return False
    
    def get_notes_by_type(self, note_type):
        """获取指定类型的所有笔记"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, note_type, title, content, created_at, updated_at
                FROM notes WHERE note_type = ?
                ORDER BY updated_at DESC
            ''', (note_type,))
            
            notes = []
            for row in cursor.fetchall():
                notes.append({
                    'id': row[0],
                    'note_type': row[1],
                    'title': row[2],
                    'content': row[3],
                    'created_at': row[4],
                    'updated_at': row[5]
                })
            
            conn.close()
            return notes
        except Exception as e:
            logger.error(f"获取笔记失败: {e}")
            return []
    
    def get_all_notes(self):
        """获取所有笔记"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, note_type, title, content, created_at, updated_at
                FROM notes ORDER BY note_type, updated_at DESC
            ''')
            
            notes = []
            for row in cursor.fetchall():
                notes.append({
                    'id': row[0],
                    'note_type': row[1],
                    'title': row[2],
                    'content': row[3],
                    'created_at': row[4],
                    'updated_at': row[5]
                })
            
            conn.close()
            return notes
        except Exception as e:
            logger.error(f"获取所有笔记失败: {e}")
            return []
    
    def get_today_notes(self):
        """获取今日的短期安排"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            conn = self.db._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, note_type, title, content, created_at, updated_at
                FROM notes 
                WHERE note_type = ? AND (created_at LIKE ? OR updated_at LIKE ?)
                ORDER BY updated_at DESC
            ''', (NoteType.SHORT_TERM, f'{today}%', f'{today}%'))
            
            notes = []
            for row in cursor.fetchall():
                notes.append({
                    'id': row[0],
                    'note_type': row[1],
                    'title': row[2],
                    'content': row[3],
                    'created_at': row[4],
                    'updated_at': row[5]
                })
            
            conn.close()
            return notes
        except Exception as e:
            logger.error(f"获取今日笔记失败: {e}")
            return []
    
    def clear_today_notes(self):
        """清除今日的短期安排"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            conn = self.db._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM notes 
                WHERE note_type = ? AND (created_at LIKE ? OR updated_at LIKE ?)
            ''', (NoteType.SHORT_TERM, f'{today}%', f'{today}%'))
            conn.commit()
            conn.close()
            
            logger.info("清除今日短期安排完成")
            return True
        except Exception as e:
            logger.error(f"清除今日笔记失败: {e}")
            return False
