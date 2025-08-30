# -*- coding: utf-8 -*-
# meta developer: @Rezoxss
# scope: hikka_only

from .. import loader, utils
import logging
import asyncio
import aiohttp
import base64
import json
from urllib.parse import quote

logger = logging.getLogger(__name__)

@loader.tds
class ShazamMod(loader.Module):
    """Shazam для распознавания музыки с бесплатными API"""
    
    strings = {
        "name": "ShazamAPI",
        "processing": "🎵 Анализирую аудио...",
        "recognized": "🎶 Найдено: {} - {}",
        "not_found": "❌ Музыка не распознана",
        "no_audio": "❌ Нет голосового сообщения",
        "error": "❌ Ошибка распознавания",
        "no_api": "❌ Не установлен API ключ",
        "downloading": "📥 Скачиваю аудио...",
        "api_help": "🔑 Получи API ключ: https://audd.io (бесплатно)"
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "api_key",
                "",
                "API ключ от AudD (бесплатный)",
                validator=loader.validators.String()
            ),
            loader.ConfigValue(
                "auto_recognition", 
                False,
                "Автораспознавание голосовых",
                validator=loader.validators.Boolean()
            ),
            loader.ConfigValue(
                "respond_to_self",
                True,  # Отвечать на свои сообщения!
                "Отвечать на свои голосовые",
                validator=loader.validators.Boolean()
            )
        )

    async def client_ready(self, client, db):
        self._client = client

    async def download_audio(self, message):
        """Скачиваем голосовое сообщение"""
        if not (message.voice or message.audio or message.video_note):
            return None
            
        try:
            file = await message.download_media(file=bytes)
            return file
        except Exception as e:
            logger.error(f"Download error: {e}")
            return None

    async def recognize_audd(self, audio_data):
        """Распознаем через AudD API (бесплатный)"""
        if not self.config["api_key"]:
            return self.strings("no_api")
            
        try:
            url = "https://api.audd.io/"
            
            form_data = aiohttp.FormData()
            form_data.add_field('api_token', self.config["api_key"])
            form_data.add_field('return', 'apple_music,spotify')
            form_data.add_field('method', 'recognize')
            form_data.add_field('file', audio_data, filename='audio.mp3', content_type='audio/mpeg')
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=form_data) as response:
                    result = await response.json()
                    
                    if result['status'] == 'success' and result['result']:
                        track = result['result']
                        artist = track.get('artist', 'Unknown Artist')
                        title = track.get('title', 'Unknown Title')
                        album = track.get('album', '')
                        
                        response_text = f"🎵 {artist} - {title}"
                        if album:
                            response_text += f"\n💿 Альбом: {album}"
                            
                        # Добавляем ссылки
                        if track.get('apple_music'):
                            response_text += f"\n🍎 Apple Music: {track['apple_music']['url']}"
                        if track.get('spotify'):
                            response_text += f"\n🟢 Spotify: {track['spotify']['external_urls']['spotify']}"
                            
                        return response_text
                    else:
                        return self.strings("not_found")
                        
        except Exception as e:
            logger.error(f"Audd error: {e}")
            return self.strings("error")

    async def recognize_music(self, audio_data):
        """Основная функция распознавания"""
        return await self.recognize_audd(audio_data)

    @loader.command()
    async def shazam(self, message):
        """Распознать музыку из голосового - ответом на сообщение"""
        reply = await message.get_reply_message()
        if not reply:
            await utils.answer(message, "❌ Ответь на голосовое сообщение")
            return
            
        await utils.answer(message, self.strings("downloading"))
        
        audio_data = await self.download_audio(reply)
        if not audio_data:
            await utils.answer(message, self.strings("no_audio"))
            return
        
        await utils.answer(message, self.strings("processing"))
        
        result = await self.recognize_music(audio_data)
        await utils.answer(message, result)

    @loader.command()
    async def shazamkey(self, message):
        """Установить API ключ AudD - .shazamkey <ключ>"""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, "❌ Укажи API ключ\n🔑 Получить: https://audd.io\n💡 Бесплатно: 100 запросов/месяц")
            return
            
        self.config["api_key"] = args
        await utils.answer(message, "✅ API ключ установлен")

    @loader.command()
    async def shazamauto(self, message):
        """Включить/выключить автораспознавание"""
        self.config["auto_recognition"] = not self.config["auto_recognition"]
        status = "✅ Включено" if self.config["auto_recognition"] else "❌ Выключено"
        await utils.answer(message, f"Автораспознавание: {status}")

    @loader.command()
    async def shazamself(self, message):
        """Включить/выключить ответы на свои сообщения"""
        self.config["respond_to_self"] = not self.config["respond_to_self"]
        status = "✅ Включено" if self.config["respond_to_self"] else "❌ Выключено"
        await utils.answer(message, f"Ответы на свои сообщения: {status}")

    @loader.command()
    async def shazamhelp(self, message):
        """Помощь по Shazam модулю"""
        help_text = (
            "🎵 ShazamAPI Help:\n\n"
            "🔑 Бесплатный API ключ:\n"
            "• AudD: https://audd.io (100 запросов/месяц)\n\n"
            "📋 Команды:\n"
            ".shazam - распознать музыку (ответом на голосовое)\n"
            ".shazamkey <key> - установить API ключ\n"
            ".shazamauto - вкл/выкл автораспознавание\n"
            ".shazamself - вкл/выкл ответы на свои сообщения\n"
            ".shazamhelp - эта справка\n\n"
            "💡 Автораспознавание работает на ВСЕ голосовые!"
        )
        await utils.answer(message, help_text)

    @loader.watcher()
    async def watcher(self, message):
        """Автораспознавание голосовых - отвечает на ВСЕ включая свои"""
        if not self.config["auto_recognition"]:
            return
            
        if message.voice or message.audio or message.video_note:
            # Проверяем настройку ответов на свои сообщения
            if message.out and not self.config["respond_to_self"]:
                return
                
            processing_msg = await message.reply(self.strings("processing"))
            
            audio_data = await self.download_audio(message)
            if not audio_data:
                await processing_msg.delete()
                return
                
            result = await self.recognize_music(audio_data)
            await processing_msg.edit(result)
