# -*- coding: utf-8 -*-
"""Проба каталога: названия уроков живут в базе, а не в исходнике страницы.

Держит обе стороны переезда 18.09.2026:
  • в `index.html` не осталось ни названий уроков, ни имён блоков — по ним
    читалась вся карта обучения, а страница открыта всякому;
  • меню, главный экран, список раздела и знаменатель прогресса собираются
    из ответа Supabase: заглушка отдаёт пять блоков, четыре готовых урока,
    один запланированный и два пустых блока.

Проверено возвращением дефекта: на прежней версии страницы проба краснеет
восемью находками — меню пустое, названия лежат в исходнике.

Запуск: python3 scratchpad/probes/check_kb_catalog.py (из корня репозитория).
"""
import json, os, pathlib, re, threading, http.server, socketserver, functools, sys
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path('/home/user/knowledge-baniamsk')
зам, отч = [], []
def факт(у, т): (отч if у else зам).append(("    ок  " if у else "") + т)

# ── в исходнике названий быть не должно ──────────────────────────────────
исходник = (КОРЕНЬ / 'index.html').read_text(encoding='utf-8')
следы = [с for с in ('Лестница Ханта', 'Belfort', 'Три доверия', 'Боли и страхи',
                     'Квалификатор', 'Что мы продаём', 'Встреча с экспертом',
                     'Блок 1. Компания', 'Блок 3. Продажи') if с in исходник]
факт(not следы, f"в исходнике нет названий уроков и блоков: {следы or 'чисто'}")

УРОКИ = [
    dict(id='lesson-1-1', block=1, ord=1, status='planned', title_ru='Первый', title_en='First',
         nav_ru='Первый', nav_en='First', sub_ru='', sub_en='', body_html=''),
    dict(id='lesson-1-3', block=1, ord=3, status='ready', title_ru='Полное имя 1.3', title_en='Full 1.3',
         nav_ru='Меню 1.3', nav_en='Nav 1.3', sub_ru='Подпись 1.3', sub_en='Sub 1.3',
         body_html='<div id="lesson-1-3"><h2>Урок 1.3</h2><p>Тело</p></div>'),
    dict(id='lesson-3-1', block=3, ord=1, status='ready', title_ru='Полное имя 3.1', title_en='Full 3.1',
         nav_ru='Меню 3.1', nav_en='Nav 3.1', sub_ru='Подпись 3.1', sub_en='Sub 3.1',
         body_html='<div id="lesson-3-1"><h2>Урок 3.1</h2><p>Тело</p></div>'),
    dict(id='lesson-3-2', block=3, ord=2, status='ready', title_ru='Полное имя 3.2', title_en='Full 3.2',
         nav_ru='Меню 3.2', nav_en='Nav 3.2', sub_ru='Подпись 3.2', sub_en='Sub 3.2',
         body_html='<div id="lesson-3-2"><h2>Урок 3.2</h2><p>Тело</p></div>'),
    dict(id='lesson-5-1', block=5, ord=1, status='ready', title_ru='Полное имя 5.1', title_en='Full 5.1',
         nav_ru='Меню 5.1', nav_en='Nav 5.1', sub_ru='Подпись 5.1', sub_en='Sub 5.1',
         body_html='<div id="lesson-5-1"><h2>Урок 5.1</h2><p>Тело</p></div>'),
]
БЛОКИ = [
    dict(id='b1', num=1, ord=1, name_ru='Первый блок', name_en='Block one', sub_ru='Про первый', sub_en='About one'),
    dict(id='b2', num=2, ord=2, name_ru='Пустой', name_en='Empty', sub_ru='', sub_en=''),
    dict(id='b3', num=3, ord=3, name_ru='Третий блок', name_en='Block three', sub_ru='Про третий', sub_en='About three'),
    dict(id='b4', num=4, ord=4, name_ru='Тоже пустой', name_en='Empty too', sub_ru='', sub_en=''),
    dict(id='b5', num=5, ord=5, name_ru='Пятый блок', name_en='Block five', sub_ru='Про пятый', sub_en='About five'),
]

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
with sync_playwright() as pw:
    бр = pw.chromium.launch(executable_path=os.environ.get('BM_CHROMIUM'), args=["--no-sandbox"])
    стр = бр.new_page(viewport={"width": 1280, "height": 900})
    стр.add_init_script(ЗАГЛУШКА)
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.goto(f"http://127.0.0.1:{порт}/", wait_until="load")
    стр.wait_for_timeout(2500)
    д = стр.evaluate("""() => ({
      групп: document.querySelectorAll('#sbNavList .sb-group').length,
      пунктов: document.querySelectorAll('#sbNavList .sb-a').length,
      выключенных: document.querySelectorAll('#sbNavList .sb-a.disabled').length,
      ссылки: [...document.querySelectorAll('#sbNavList .sb-a[id]')].map(э => э.id),
      галочки: document.querySelectorAll('#sbNavList .sb-a-check').length,
      имена: [...document.querySelectorAll('#sbNavList .sb-a .lang-ru')].map(э => э.textContent),
      заголовкиГрупп: [...document.querySelectorAll('#sbNavList .sb-group .lang-ru')].map(э => э.textContent),
      всегоУроков: (typeof TOTAL_LESSONS !== 'undefined') ? TOTAL_LESSONS : null,
      каталог: (typeof KB_LESSONS !== 'undefined') ? KB_LESSONS.map(l => l.id) : null,
      блоковНаГлавной: (typeof HS_BLOCKS !== 'undefined') ? HS_BLOCKS.map(b => b.id) : null,
      карточек: document.querySelectorAll('#homeScreen .hs-card, #homeScreen [onclick^="openSection"]').length,
      экранВхода: document.getElementById('authOverlay').classList.contains('on'),
      знаменатель: (document.getElementById('sbProgTotal') || {}).textContent
    })""")
    print(json.dumps(д, ensure_ascii=False, indent=1))
    факт(д['групп'] == 5, f"групп в меню: {д['групп']} (ждём 5)")
    факт(д['пунктов'] == 7, f"пунктов: {д['пунктов']} — 4 урока, 1 запланированный, 2 заглушки пустых блоков")
    факт(д['ссылки'] == ['navL13','navL31','navL32','navL51'], f"имена узлов: {д['ссылки']}")
    факт(д['галочки'] == 4, f"галочек: {д['галочки']} (по одной на готовый урок)")
    факт('Меню 3.1' in д['имена'] and 'Полное имя 3.1' not in д['имена'],
         "в меню стоит короткое имя из nav_ru, а не полное")
    факт(д['всегоУроков'] == 4, f"TOTAL_LESSONS: {д['всегоУроков']}")
    факт(д['блоковНаГлавной'] == ['b1','b3','b5'], f"на главной блоки: {д['блоковНаГлавной']}")
    факт(any('Первый блок' in з for з in д['заголовкиГрупп']), f"заголовки групп: {д['заголовкиГрупп']}")
    факт(not д['экранВхода'], "экран входа закрыт после входа")
    факт(д['знаменатель'] == '4', f"знаменатель прогресса из базы: {д['знаменатель']} (ждём 4)")

    # открыть урок из меню
    стр.click('#navL31'); стр.wait_for_timeout(500)
    у = стр.evaluate("""() => ({
      виденУрок: (document.getElementById('lesson-3-1') || {}).style?.display,
      подсвечен: document.getElementById('navL31').classList.contains('on'),
      заголовок: (document.querySelector('#lesson-3-1 h2') || {}).textContent || ''
    })""")
    факт(у['виденУрок'] == 'block' and у['подсвечен'], f"урок открылся и подсвечен: {у}")
    факт('3.1' in у['заголовок'], f"тело урока подставлено: {у['заголовок']!r}")

    # список раздела: полные названия из каталога
    стр.evaluate("() => { showHomeScreen(); openSection('b3'); }"); стр.wait_for_timeout(400)
    р = стр.evaluate("""() => [...document.querySelectorAll('#secLessonList .slr-title .lang-ru')].map(э => э.textContent)""")
    факт(р == ['Полное имя 3.1', 'Полное имя 3.2'], f"в списке раздела полные названия: {р}")
    стр.screenshot(path=str(pathlib.Path(__file__).parent / 'каталог.png'))
    бр.close()
с.shutdown()

важные = [о for о in ошибки if 'favicon' not in о]
факт(not важные, f"ошибок страницы нет: {важные[:2]}")
print("\n".join(отч)); print()
print("\n".join("ЗАМЕЧАНИЕ: " + з for з in зам) if зам else "Замечаний нет")
sys.exit(1 if зам else 0)
