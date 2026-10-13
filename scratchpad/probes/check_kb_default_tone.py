# -*- coding: utf-8 -*-
"""Проба цвета базы знаний: по своей ссылке — «Зелёный-графит».

Константин 13.10.2026: «Базу знаний сделай по умолчанию Зеленый-графит
цветовую схему. Когда человек по её ссылке заходит. А если из калькулятора,
то цвет темы калькулятора».

Держит обе стороны:
  • открытая по своему адресу база — признак тона bmsk, графитовое боковое
    меню, фирменный цвет (--g) зелёный, а не бирюзовый, днём и ночью;
  • открытая калькулятором (?embed=1) база сама ничего не перекрашивает:
    цвет ей присылает калькулятор, и до его сообщения она остаётся как была.

Снимки 1440 px — рядом с пробой.

Запуск: python3 scratchpad/probes/check_kb_default_tone.py (из корня репозитория).
"""
import colorsys, json, os, pathlib, threading, http.server, socketserver, functools, sys
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get('BM_KB') or '/home/user/knowledge-baniamsk')
ЗДЕСЬ = pathlib.Path(__file__).parent
зам, отч = [], []
def факт(у, т): (отч if у else зам).append(("    ок  " if у else "") + т)

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
                 : имя === 'kb_blocks' ? window.__блоки
                 : имя === 'profiles' ? [{ id:'u1', email:'m@baniamsk.ru', full_name:'Проба', role:'manager' }] : [];
    const ответ = { data: данные, error: null };
    const цепь = { select: () => цепь, order: () => цепь, eq: () => цепь, is: () => цепь,
      maybeSingle: async () => ({ data: данные[0] || null, error: null }),
      single: async () => ({ data: данные[0] || null, error: null }),
      then: (ф, о) => Promise.resolve(ответ).then(ф, о) };
    return { select: () => цепь, upsert: async () => ({ error: null }), update: () => цепь, insert: async () => ({ error: null }) };
  }
}) };
""" % (json.dumps(УРОКИ, ensure_ascii=False), json.dumps(БЛОКИ, ensure_ascii=False))
ВИД = """() => {
  const к = s => { const м = /rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)/.exec(s); return м ? [+м[1], +м[2], +м[3]] : null; };
  const g = getComputedStyle(document.documentElement).getPropertyValue('--g').trim();
  const пробник = document.createElement('i'); пробник.style.color = 'var(--g)'; document.body.appendChild(пробник);
  const цвет = getComputedStyle(пробник).color; пробник.remove();
  return { тон: document.documentElement.dataset.tone || '', g, цвет: к(цвет),
           меню: к(getComputedStyle(document.getElementById('sidebar')).backgroundColor) };
}"""


def оттенок(rgb):
    h, l, s = colorsys.rgb_to_hls(*(x / 255 for x in rgb))
    return round(h * 360)


класс = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(КОРЕНЬ))
class Тихий(класс.func):
    def log_message(self, *а): pass
socketserver.TCPServer.allow_reuse_address = True
с = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Тихий, directory=str(КОРЕНЬ)))
threading.Thread(target=с.serve_forever, daemon=True).start()
порт = с.server_address[1]
ошибки = []
хром = os.environ.get('BM_CHROMIUM') or str(sorted(pathlib.Path('/opt/pw-browsers').glob('chromium-*/chrome-linux/chrome'))[-1])
with sync_playwright() as pw:
    бр = pw.chromium.launch(executable_path=хром, args=["--no-sandbox"])
    for схема in ('light', 'dark'):
        стр = бр.new_page(viewport={"width": 1440, "height": 900}, color_scheme=схема)
        стр.add_init_script(ЗАГЛУШКА)
        стр.on("pageerror", lambda e: ошибки.append(str(e)))
        стр.goto(f"http://127.0.0.1:{порт}/", wait_until="load"); стр.wait_for_timeout(1800)
        в = стр.evaluate(ВИД)
        отч.append(f"    {схема} своя ссылка: {в}")
        факт(в['тон'] == 'bmsk', f"[{схема}] своя ссылка: признак тона bmsk ({в['тон']!r})")
        факт(в['меню'] == [36, 39, 31], f"[{схема}] своя ссылка: боковое меню графитовое {в['меню']}")
        факт(в['цвет'] and 70 <= оттенок(в['цвет']) <= 110, f"[{схема}] своя ссылка: фирменный цвет зелёный, оттенок {в['цвет'] and оттенок(в['цвет'])}°")
        if not os.environ.get('BM_KB'): стр.screenshot(path=str(ЗДЕСЬ / f"тон-своя-ссылка-{схема}.png"))
        стр.close()
    стр = бр.new_page(viewport={"width": 1440, "height": 900})
    стр.add_init_script(ЗАГЛУШКА)
    стр.goto(f"http://127.0.0.1:{порт}/?embed=1", wait_until="load"); стр.wait_for_timeout(1500)
    в = стр.evaluate(ВИД)
    факт(в['тон'] == '', f"в калькуляторе: признака тона до сообщения калькулятора нет ({в['тон']!r})")
    факт(в['цвет'] and 175 <= оттенок(в['цвет']) <= 195, f"в калькуляторе: сама база не перекрашена, оттенок {в['цвет'] and оттенок(в['цвет'])}°")
    стр.close()
    бр.close()
с.shutdown()
факт(not ошибки, f"ошибок страницы нет: {ошибки[:3]}")
print("\n".join(отч))
if зам:
    print("НАХОДКИ:"); [print("  ✗", з) for з in зам]; sys.exit(1)
print("Чисто: по своей ссылке база — в «Зелёном-графите» днём и ночью; в калькуляторе цвет не трогает, ждёт калькулятор.")
