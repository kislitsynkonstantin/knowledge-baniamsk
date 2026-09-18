# -*- coding: utf-8 -*-
"""Печать инструкции в PDF — в двух видах: мобильном и A4.

PDF не переверстывается под окно читателя: это лист с закреплёнными
координатами, медиа-запросов в нём нет. Поэтому вид выбирается при печати, а
не при открытии, и файлов получается два. По-настоящему подстраивается только
сама страница на домене — её и стоит давать ссылкой.

Мобильный вид: лист 110×200 мм, та же одна колонка и тот же ритм, что на
телефоне. A4: собственные поля документа из его же печатных стилей.

Запуск из корня репозитория:
    python3 scratchpad/сделать-pdf.py [куда-класть]
"""
import functools
import http.server
import os
import pathlib
import socketserver
import sys
import threading

from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(__file__).resolve().parent.parent
СТРАНИЦА = 'podpisanie/'
ИМЯ = 'Подписание документов через Telegram — С-ПД, версия 3'

# Мобильный лист: ширина колонки та же, что у картинок в документе (95 мм),
# плюс поля. Разрывы страниц документ держит сам — у шагов и плашек стоит
# `break-inside: avoid`, поэтому ни один шаг не рвётся пополам.
ТЕЛЕФОН = ('@page{size:110mm 200mm !important; margin:9mm 8mm 10mm 8mm !important}'
           ' body{font-size:10.6pt !important} .shot{max-width:94mm !important}')


def сервер():
    класс = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(КОРЕНЬ))
    socketserver.TCPServer.allow_reuse_address = True
    с = socketserver.TCPServer(('127.0.0.1', 0), класс)
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


def напечатать(куда):
    с, порт = сервер()
    сделано = []
    try:
        with sync_playwright() as pw:
            бр = pw.chromium.launch(executable_path=os.environ.get('BM_CHROMIUM'),
                                    args=['--no-sandbox'])
            for вид, стиль in (('мобильный', ТЕЛЕФОН), ('A4', None)):
                стр = бр.new_page()
                стр.goto(f'http://127.0.0.1:{порт}/{СТРАНИЦА}', wait_until='load')
                стр.wait_for_timeout(1200)
                if стиль:
                    стр.add_style_tag(content=стиль)
                стр.emulate_media(media='print')
                путь = куда / f'{ИМЯ}, {вид}.pdf'
                стр.pdf(path=str(путь), prefer_css_page_size=True, print_background=True)
                стр.close()
                сделано.append(путь)
            бр.close()
    finally:
        с.shutdown()
    return сделано


if __name__ == '__main__':
    куда = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path('.')
    for п in напечатать(куда):
        print(f'{п.name} — {п.stat().st_size // 1024} КБ')
