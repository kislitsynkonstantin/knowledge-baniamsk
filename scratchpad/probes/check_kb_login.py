# -*- coding: utf-8 -*-
"""Проба окна входа базы знаний: лист калькулятора, ожидание с полоской.

Константин 13.10.2026, снимком прежнего окна входа: «И окно входа в базу
знаний сделай в стиле калькулятора окно, с полоской загрузки как там».

Держит, на 390, 768 и 1440 px, днём и ночью:
  • окно собрано из листа калькулятора: логотип, надзаголовок «Вход для
    сотрудников», «База знаний», поля с линией снизу (без рамки вокруг);
  • лист не шире 420 px, ничего не вылезает за экран, поля нажатия не
    меньше 32 px (поля ввода — 44);
  • кнопка «Войти» — в «Зелёном-графите» по своей ссылке, логотип загружен
    и виден один (дневной или ночной);
  • нажатие «Войти»: кнопка ждёт — знак вращения, «Проверяем…», бегущая
    полоска по нижнему краю, поля только для чтения;
  • неверный пароль — плашка «Неверный email или пароль», кнопка снова «Войти»;
  • верный — окно уходит, встаёт полоска «Загрузка материалов…».

Снимки — рядом с пробой. Шрифты — настоящие (шрифты_google.css калькулятора).

Запуск: python3 scratchpad/probes/check_kb_login.py (из корня репозитория).
"""
import colorsys, os, pathlib, threading, http.server, socketserver, functools, sys
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get('BM_KB') or '/home/user/knowledge-baniamsk')
ЗДЕСЬ = pathlib.Path(__file__).parent
ШРИФТЫ = pathlib.Path(os.environ.get('BM_FONTS_CSS') or '/home/user/-calculator-test/scratchpad/probes/шрифты_google.css')
зам, отч = [], []
def факт(у, т): (отч if у else зам).append(("    ок  " if у else "") + т)

ЗАГЛУШКА = """
window.__вход = { сессия: null, ждать: 900, пароль: 'верный' };
const _сессия = { user: { id: 'u1', email: 'm@baniamsk.ru' }, access_token: 't' };
window.supabase = { createClient: () => ({
  auth: {
    getSession: async () => ({ data: { session: window.__вход.сессия } }),
    onAuthStateChange: () => ({ data: { subscription: { unsubscribe(){} } } }),
    signInWithPassword: (а) => new Promise(r => setTimeout(() => r(а.password === window.__вход.пароль
      ? { data: { user: _сессия.user, session: _сессия }, error: null }
      : { data: null, error: { message: 'Invalid login credentials' } }), window.__вход.ждать)),
    setSession: async () => ({ data: { session: _сессия }, error: null }),
    signOut: async () => ({})
  },
  from: (имя) => {
    const ответ = { data: имя === 'profiles' ? [{ id:'u1', email:'m@baniamsk.ru', full_name:'Проба', role:'manager' }] : [], error: null };
    const ждать = имя === 'kb_lessons' ? 2500 : 0;
    const цепь = { select: () => цепь, order: () => цепь, eq: () => цепь, is: () => цепь,
      maybeSingle: async () => ({ data: ответ.data[0] || null, error: null }),
      single: async () => ({ data: ответ.data[0] || null, error: null }),
      then: (ф, о) => new Promise(r => setTimeout(() => r(ответ), ждать)).then(ф, о) };
    return { select: () => цепь, upsert: async () => ({ error: null }), update: () => цепь, insert: async () => ({ error: null }) };
  }
}) };
"""
ВИД = """() => {
  const ов = document.getElementById('authOverlay'), л = ов.querySelector('.lg-paper'), к = document.getElementById('authBtn');
  const r = л.getBoundingClientRect(), w = innerWidth;
  const видимые = [...ов.querySelectorAll('*')].filter(э => э.getClientRects().length && getComputedStyle(э).visibility !== 'hidden');
  const вылез = видимые.filter(э => { const б = э.getBoundingClientRect(); return б.width && (б.left < -0.5 || б.right > w + 0.5); }).map(э => э.className || э.tagName);
  const поле = э => { const б = э.getBoundingClientRect(), п = getComputedStyle(э, '::before');
    const и = п.content !== 'none' && п.position === 'absolute' ? п : null;
    const доп = s => и ? -parseFloat(s) || 0 : 0;
    return [Math.round(б.width + доп(и && и.left) + доп(и && и.right)), Math.round(б.height + доп(и && и.top) + доп(и && и.bottom))]; };
  const кнопки = [...ов.querySelectorAll('button')].filter(э => э.getClientRects().length).map(э => ({ кто: э.id || э.className, поле: поле(э) }));
  const логотипы = [...ов.querySelectorAll('.lg-logo')].filter(э => getComputedStyle(э).display !== 'none');
  const вход = document.getElementById('authEmail'), сб = getComputedStyle(вход);
  const к_ = s => { const м = /rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)/.exec(s); return м ? [+м[1], +м[2], +м[3]] : null; };
  return { открыто: ов.classList.contains('on') && getComputedStyle(ов).display !== 'none',
    лист: [Math.round(r.width), Math.round(r.left), Math.round(w - r.right)],
    вылез, кнопки, переполнение: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    логотипов: логотипы.length, логотипЗагружен: логотипы.every(э => э.complete && э.naturalWidth > 0),
    надзаголовок: (ов.querySelector('.lg-eyebrow .lang-ru') || {}).textContent,
    заголовок: (ов.querySelector('.lg-title .lang-ru') || {}).textContent,
    рамкаПоля: [сб.borderTopWidth, сб.borderLeftWidth, сб.borderBottomWidth], высотаПоля: Math.round(вход.getBoundingClientRect().height),
    кнопка: к_(getComputedStyle(к).backgroundColor), шрифт: getComputedStyle(ов.querySelector('.lg-title')).fontFamily };
}"""


def оттенок(rgb):
    h, l, s = colorsys.rgb_to_hls(*(x / 255 for x in rgb))
    return round(h * 360), s


class Тихий(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *а): pass
socketserver.TCPServer.allow_reuse_address = True
с = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Тихий, directory=str(КОРЕНЬ)))
threading.Thread(target=с.serve_forever, daemon=True).start()
порт = с.server_address[1]
ошибки = []
хром = os.environ.get('BM_CHROMIUM') or str(sorted(pathlib.Path('/opt/pw-browsers').glob('chromium-*/chrome-linux/chrome'))[-1])
css = ШРИФТЫ.read_text(encoding='utf-8') if ШРИФТЫ.exists() else ''
with sync_playwright() as pw:
    бр = pw.chromium.launch(executable_path=хром, args=["--no-sandbox"])
    for ш, в in ((390, 844), (768, 1000), (1440, 900)):
        for схема in ('light', 'dark'):
            н = f"[{ш} {схема}]"
            стр = бр.new_page(viewport={"width": ш, "height": в}, color_scheme=схема, device_scale_factor=2 if ш == 1440 else 1)
            if css:
                стр.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="text/css", body=css))
                стр.route("**/fonts.gstatic.com/**", lambda r: r.abort())
            стр.add_init_script(ЗАГЛУШКА)
            стр.on("pageerror", lambda e: ошибки.append(str(e)))
            стр.goto(f"http://127.0.0.1:{порт}/", wait_until="load"); стр.wait_for_timeout(1500)
            д = стр.evaluate(ВИД)
            факт(д['открыто'], f"{н} окно входа открыто")
            факт(д['надзаголовок'] == 'Вход для сотрудников' and д['заголовок'] == 'База знаний', f"{н} надзаголовок и заголовок листа: {д['надзаголовок']!r}, {д['заголовок']!r}")
            факт(д['лист'][0] <= 420 and д['лист'][1] >= 13 and д['лист'][2] >= 13, f"{н} лист {д['лист'][0]} px, поля {д['лист'][1]}/{д['лист'][2]} px")
            факт(not д['вылез'] and д['переполнение'] <= 0, f"{н} ничего не вылезает: {д['вылез']}, переполнение {д['переполнение']}")
            мелкие = [к for к in д['кнопки'] if min(к['поле']) < 32]
            факт(not мелкие, f"{н} поля нажатия ≥ 32 px: {мелкие or [к['поле'] for к in д['кнопки']]}")
            факт(д['рамкаПоля'][:2] == ['0px', '0px'] and д['рамкаПоля'][2] == '1px' and д['высотаПоля'] >= 44,
                 f"{н} поле — линия снизу, без рамки, высота {д['высотаПоля']}: {д['рамкаПоля']}")
            факт(д['логотипов'] == 1 and д['логотипЗагружен'], f"{н} виден один логотип, загружен: {д['логотипов']}, {д['логотипЗагружен']}")
            h, s = оттенок(д['кнопка'])
            факт(70 <= h <= 110, f"{н} кнопка «Войти» зелёная: оттенок {h}° ({д['кнопка']})")
            факт('Unbounded' in д['шрифт'], f"{н} заголовок — Unbounded: {д['шрифт'][:30]}")
            стр.screenshot(path=str(ЗДЕСЬ / f"вход-{ш}-{схема}.png"))
            if ш == 390 and схема == 'light' or ш == 1440 and схема == 'dark':
                # неверный пароль
                стр.fill('#authEmail', 'm@baniamsk.ru'); стр.fill('#authPwd', 'неверный')
                стр.click('#authBtn'); стр.wait_for_timeout(250)
                ж = стр.evaluate("""() => { const к = document.getElementById('authBtn'), п = getComputedStyle(к, '::after');
                  return { ждёт: к.classList.contains('wait'), знак: !!к.querySelector('.lg-spin'), текст: к.innerText.trim(),
                           полоска: п.content !== 'none' && parseFloat(п.height) >= 2 && п.animationName !== 'none',
                           толькоЧтение: document.getElementById('authPwd').readOnly }; }""")
                факт(ж['ждёт'] and ж['знак'] and ж['полоска'] and ж['толькоЧтение'] and 'Проверяем' in ж['текст'].capitalize(),
                     f"{н} ожидание: знак, «Проверяем…», бегущая полоска, поля только для чтения: {ж}")
                стр.screenshot(path=str(ЗДЕСЬ / f"вход-ждём-{ш}-{схема}.png"))
                стр.wait_for_timeout(1100)
                о = стр.evaluate("""() => ({ ошибка: getComputedStyle(document.getElementById('authErr')).display !== 'none' ? document.getElementById('authErr').textContent : '',
                  ждёт: document.getElementById('authBtn').classList.contains('wait'), текст: document.getElementById('authBtn').innerText.trim() })""")
                факт(о['ошибка'] == 'Неверный email или пароль' and not о['ждёт'] and о['текст'].lower() == 'войти',
                     f"{н} неверный пароль: плашка и снова «Войти»: {о}")
                # верный
                стр.fill('#authPwd', 'верный'); стр.click('#authBtn'); стр.wait_for_timeout(1300)
                у = стр.evaluate("""() => ({ окно: document.getElementById('authOverlay').classList.contains('on'),
                  полоска: !!document.querySelector('#loadingState .kb-load') && getComputedStyle(document.getElementById('loadingState')).display !== 'none',
                  текст: (document.getElementById('loadingState') || {}).innerText || '' })""")
                факт(not у['окно'] and у['полоска'] and 'Загрузка материалов' in у['текст'], f"{н} верный пароль: окно ушло, полоска загрузки материалов: {у}")
            стр.close()
    бр.close()
с.shutdown()
факт(not ошибки, f"ошибок страницы нет: {ошибки[:3]}")
print("\n".join(отч))
if зам:
    print("НАХОДКИ:"); [print("  ✗", з) for з in зам]; sys.exit(1)
print("Чисто: окно входа — лист калькулятора на 390/768/1440 днём и ночью, в «Зелёном-графите»; ожидание со знаком и бегущей полоской, ошибка и вход отрабатывают.")
