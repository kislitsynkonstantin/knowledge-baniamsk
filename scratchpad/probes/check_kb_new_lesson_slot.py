# -*- coding: utf-8 -*-
"""Урок, которому в разметке страницы нет места, всё равно открывается.

Константин 16.10.2026: «Добавь эти документы в базу знаний для менеджеров».
Тела уроков приходят из kb_lessons и подставляются в пустые контейнеры
lesson-N-M, которые стояли в index.html. Урок с новым номером (2.1, 3.12)
контейнера не имел: меню и каталог его знали, а нажатие открывало пустоту.
Теперь контейнер создаётся при загрузке.

Держит, на заглушке базы:
  • урок 2.1 и урок 3.12 — без контейнера в разметке — открываются из меню,
    тело видно, заголовок урока на месте;
  • у них работает отметка «пройден»: кнопка меняет состояние блока;
  • поиск по базе находит раздел урока 3.12;
  • прежний урок 3.1 с контейнером в разметке открывается как раньше.

Проверено возвращением дефекта: на прежней странице — находки по обоим
новым урокам.

Запуск: python3 scratchpad/probes/check_kb_new_lesson_slot.py (из корня репозитория).
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


УРОКИ = [
    dict(id='lesson-2-1', block=2, ord=1, status='ready', title_ru='Урок без места 2.1', title_en='Slotless 2.1',
         nav_ru='Меню 2.1', nav_en='Nav 2.1', sub_ru='', sub_en='', body_html=тело('lesson-2-1', '2.1', 'Урок без места 2.1', 'Раздел два-один')),
    dict(id='lesson-3-1', block=3, ord=1, status='ready', title_ru='Полное имя 3.1', title_en='Full 3.1',
         nav_ru='Меню 3.1', nav_en='Nav 3.1', sub_ru='', sub_en='', body_html=тело('lesson-3-1', '3.1', 'Урок с местом 3.1', 'Раздел три-один')),
    dict(id='lesson-3-12', block=3, ord=12, status='ready', title_ru='Урок без места 3.12', title_en='Slotless 3.12',
         nav_ru='Меню 3.12', nav_en='Nav 3.12', sub_ru='', sub_en='', body_html=тело('lesson-3-12', '3.12', 'Урок без места 3.12', 'Сценарий встречи в шоуруме')),
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
    const данные = имя === 'kb_lessons' ? window.__уроки
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
    return { select: () => цепь, upsert: async () => ({ error: null }),
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
УРОК = """(ид) => { const э = document.getElementById(ид);
  return { есть: !!э, виден: !!э && э.style.display === 'block' && э.getClientRects().length > 0,
           заголовок: э ? ((э.querySelector('h2 .lang-ru') || {}).textContent || '') : '' }; }"""
with sync_playwright() as pw:
    бр = pw.chromium.launch(executable_path=os.environ.get('BM_CHROMIUM'), args=["--no-sandbox"])
    стр = бр.new_page(viewport={"width": 1280, "height": 900})
    стр.add_init_script(ЗАГЛУШКА)
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.goto(f"http://127.0.0.1:{порт}/", wait_until="load")
    стр.wait_for_timeout(2500)
    for н, имя in (('2.1', 'Урок без места 2.1'), ('3.12', 'Урок без места 3.12'), ('3.1', 'Урок с местом 3.1')):
        узел = 'navL' + н.replace('.', '')
        if стр.locator('#' + узел).count():
            стр.click('#' + узел); стр.wait_for_timeout(400)
        у = стр.evaluate(УРОК, 'lesson-' + н.replace('.', '-'))
        факт(у['виден'] and у['заголовок'] == имя, f"урок {н} открывается из меню, тело на месте: {у}")
        if н != '3.1':
            к = н.replace('.', '-')
            стр.evaluate(f"() => {{ const б = document.getElementById('completeBtn-{к}'); if (б) б.click(); }}"); стр.wait_for_timeout(200)
            отм = стр.evaluate(f"() => {{ const б = document.getElementById('completeBox-{к}'); return !!б && б.classList.contains('done'); }}")
            факт(отм, f"урок {н}: отметка «пройден» ставится")
    найдено = стр.evaluate("""() => { try { const и = buildKbIndex(); return и.filter(з => /шоуруме/.test(з.text_ru || '')).map(з => з.lid); } catch (e) { return ['ошибка: ' + e.message]; } }""")
    факт('3.12' in найдено, f"поиск находит раздел урока 3.12: {найдено}")
    бр.close()
с.shutdown()

важные = [о for о in ошибки if 'favicon' not in о]
факт(not важные, f"ошибок страницы нет: {важные[:2]}")
print("\n".join(отч)); print()
print("\n".join("ЗАМЕЧАНИЕ: " + з for з in зам) if зам else "Замечаний нет")
sys.exit(1 if зам else 0)
