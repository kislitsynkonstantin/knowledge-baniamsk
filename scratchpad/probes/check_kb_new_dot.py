# -*- coding: utf-8 -*-
"""Новые уроки помечены в меню жёлтой точкой, пока их не открыли.

Константин 16.10.2026, снимком бокового меню: «Я тебе скинул 6 документов.
Напиши, под какими номерами они находятся и поставь возле них точки (как мы
ставим в Журнале обновлений возле названия документа)».

Новый урок — добавлен в базу меньше месяца назад (kb_lessons.added_at) и этим
сотрудником ещё не открывался (строки в kb_lesson_progress нет).

Держит, на заглушке базы:
  • у нового неоткрытого урока точка видна, у старого — нет;
  • у нового урока, который уже открывали (строка прогресса есть), точки нет;
  • точка стоит в правом поле пункта меню и не заходит на название;
  • открытие нового урока гасит точку и записывает прогресс в базу
    (status = in_progress), чтобы точка не вернулась на другом устройстве;
  • открытый урок не считается пройденным: на главной «0 из …» не меняется.

Запуск: python3 scratchpad/probes/check_kb_new_dot.py (из корня репозитория).
"""
import json, os, pathlib, threading, http.server, socketserver, functools, sys
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get('BM_ROOT') or '/home/user/knowledge-baniamsk')
зам, отч = [], []
def факт(у, т): (отч if у else зам).append(("    ок  " if у else "") + т)


def тело(ид, н, заголовок, раздел):
    к = н.replace('.', '-')
    return (f'<div id="{ид}" style="display:none;"><div class="tag"><span class="lang-ru">Урок {н}</span><span class="lang-en">Lesson {н}</span></div>'
            f'<h2><span class="lang-ru">{заголовок}</span><span class="lang-en">Title {н}</span></h2>'
            f'<h3><span class="num">1.</span><span class="lang-ru">{раздел}</span><span class="lang-en">Section</span></h3>'
            f'<p><span class="lang-ru">Текст урока {н}.</span><span class="lang-en">Lesson text {н}.</span></p>'
            f'<div class="mark-complete" id="completeBox-{к}"><div class="mc-text"><h4><span class="lang-ru">Отметить урок как пройденный</span><span class="lang-en">Mark</span></h4></div>'
            f'<button class="mc-btn" id="completeBtn-{к}" onclick="toggleComplete(\'{н}\')"><span class="lang-ru">Отметить</span><span class="lang-en">Mark complete</span></button></div></div>')


НЕДАВНО = '2026-10-16T09:00:00Z'
УРОКИ = [
    dict(id='lesson-2-1', block=2, ord=1, status='ready', title_ru='Урок без места 2.1', title_en='Slotless 2.1',
         nav_ru='Меню 2.1', nav_en='Nav 2.1', sub_ru='', sub_en='', added_at=НЕДАВНО, body_html=тело('lesson-2-1', '2.1', 'Урок без места 2.1', 'Раздел два-один')),
    dict(id='lesson-3-1', block=3, ord=1, status='ready', title_ru='Полное имя 3.1', title_en='Full 3.1',
         nav_ru='Меню 3.1', nav_en='Nav 3.1', sub_ru='', sub_en='', added_at='2026-09-01T00:00:00Z', body_html=тело('lesson-3-1', '3.1', 'Урок с местом 3.1', 'Раздел три-один')),
    dict(id='lesson-3-13', block=3, ord=13, status='ready', title_ru='Открытый новый 3.13', title_en='Opened new 3.13',
         nav_ru='Меню 3.13', nav_en='Nav 3.13', sub_ru='', sub_en='', added_at=НЕДАВНО, body_html=тело('lesson-3-13', '3.13', 'Открытый новый 3.13', 'Раздел')),
    dict(id='lesson-3-12', block=3, ord=12, status='ready', title_ru='Урок без места 3.12', title_en='Slotless 3.12',
         nav_ru='Меню 3.12', nav_en='Nav 3.12', sub_ru='', sub_en='', added_at=НЕДАВНО, body_html=тело('lesson-3-12', '3.12', 'Урок без места 3.12', 'Сценарий встречи в шоуруме')),
]
БЛОКИ = [dict(id='b%d' % н, num=н, ord=н, name_ru='Блок %d' % н, name_en='Block %d' % н, sub_ru='', sub_en='') for н in (1, 2, 3, 4, 5)]

ЗАГЛУШКА = """
window.__уроки = %s; window.__блоки = %s;
const _сессия = { user: { id: 'u1', email: 'm@baniamsk.ru' }, access_token: 't' };
window.supabase = { createClient: () => ({
  auth: {
    getSession: async () => ({ data: { session: _сессия } }),
    onAuthStateChange: () => ({ data: { subscription: { unsubscribe(){} } } }),
    signInWithPassword: async () => ({ data: { session: _сессия }, error: null }),
    setSession: async () => ({ data: { session: _сессия }, error: null }),
    signOut: async () => ({})
  },
  from: (имя) => {
    const данные = имя === 'kb_lesson_progress' ? [{ user_id: 'u1', lesson_id: '3.13', status: 'in_progress' }]
                 : имя === 'kb_lessons' ? window.__уроки
                 : имя === 'kb_blocks'  ? window.__блоки
                 : имя === 'profiles'   ? [{ id:'u1', email:'m@baniamsk.ru', full_name:'Проба', role:'manager' }]
                 : [];
    const ответ = { data: данные, error: null };
    const цепь = {
      select: () => цепь, order: () => цепь, eq: () => цепь, is: () => цепь,
      maybeSingle: async () => ({ data: данные[0] || null, error: null }),
      single: async () => ({ data: данные[0] || null, error: null }),
      then: (ф, о) => Promise.resolve(ответ).then(ф, о)
    };
    return { select: () => цепь, upsert: async (з) => { (window.__записи = window.__записи || []).push([имя, з]); return { error: null }; },
             update: () => цепь, insert: async () => ({ error: null }) };
  }
}) };
""" % (json.dumps(УРОКИ, ensure_ascii=False), json.dumps(БЛОКИ, ensure_ascii=False))

класс = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(КОРЕНЬ))
socketserver.TCPServer.allow_reuse_address = True
с = socketserver.TCPServer(("127.0.0.1", 0), класс)
threading.Thread(target=с.serve_forever, daemon=True).start()
порт = с.server_address[1]
ошибки = []
ТОЧКИ = """() => { const р = {}; ['21', '31', '312', '313'].forEach(к => { const т = document.getElementById('newL' + к), п = document.getElementById('navL' + к);
  const вид = !!т && т.style.display !== 'none' && т.getClientRects().length > 0;
  let зазор = null; if (вид && п) { const тр = т.getBoundingClientRect(); const имя = [...п.querySelectorAll('.lang-ru')].find(с => с.getClientRects().length);
    if (имя) зазор = Math.round(тр.left - имя.getBoundingClientRect().right); }
  let кол = null; if (вид) { const ш = document.querySelector('.sb-group-chevron'); if (ш) { const а = т.getBoundingClientRect(), б = ш.getBoundingClientRect(); кол = Math.round(Math.abs((а.left + а.right) / 2 - (б.left + б.right) / 2)); } }
  р[к] = { вид, зазор, кол }; }); return р; }"""
with sync_playwright() as pw:
    бр = pw.chromium.launch(executable_path=os.environ.get('BM_CHROMIUM'), args=["--no-sandbox"])
    стр = бр.new_page(viewport={"width": 1280, "height": 900})
    стр.add_init_script(ЗАГЛУШКА)
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.goto(f"http://127.0.0.1:{порт}/", wait_until="load")
    стр.wait_for_timeout(2500)
    т = стр.evaluate(ТОЧКИ)
    факт(т['21']['вид'] and т['312']['вид'], f"у новых неоткрытых 2.1 и 3.12 точка видна: {т['21']}, {т['312']}")
    факт(not т['31']['вид'], f"у старого урока 3.1 точки нет: {т['31']}")
    факт(not т['313']['вид'], f"у нового урока 3.13, который уже открывали, точки нет: {т['313']}")
    факт(all((т[к]['кол'] or 0) <= 3 for к in ('21', '312')), f"точка в колонке стрелок блоков, а не у края меню: смещение {т['21']['кол']}, {т['312']['кол']} px")
    факт(all(т[к]['зазор'] is None or т[к]['зазор'] >= 4 for к in ('21', '312')), f"точка не заходит на название: зазор {т['21']['зазор']}, {т['312']['зазор']} px")
    стр.evaluate("() => goLesson('3.12')"); стр.wait_for_timeout(400)
    т = стр.evaluate(ТОЧКИ)
    записи = стр.evaluate("() => (window.__записи || []).filter(з => з[0] === 'kb_lesson_progress').map(з => з[1])")
    факт(not т['312']['вид'] and т['21']['вид'], f"открытие 3.12 гасит его точку, у 2.1 остаётся: {т['312']}, {т['21']}")
    факт(any(з.get('lesson_id') == '3.12' and з.get('status') == 'in_progress' for з in записи), f"открытие записано в прогресс: {записи}")
    стр.evaluate("() => showHomeScreen()"); стр.wait_for_timeout(300)
    метка = стр.evaluate("() => (document.getElementById('hsProgLabel') || {}).innerText || ''")
    факт(метка.strip().startswith('0'), f"открытый урок не считается пройденным: «{метка.strip()}»")
    бр.close()
с.shutdown()

важные = [о for о in ошибки if 'favicon' not in о]
факт(not важные, f"ошибок страницы нет: {важные[:2]}")
print("\n".join(отч)); print()
print("\n".join("ЗАМЕЧАНИЕ: " + з for з in зам) if зам else "Замечаний нет")
sys.exit(1 if зам else 0)
