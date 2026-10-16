# -*- coding: utf-8 -*-
"""База знаний в калькуляторе грузит уроки один раз и полоску загрузки не перезапускает.

Константин 16.10.2026: «Ещё база при загрузке стала мигать, раньше такого не было».
В калькуляторе базу просят загрузиться дважды почти одновременно: init() по своей
сессии и сообщение auth от калькулятора. Оба вызова качали все тела уроков — после
шести новых уроков это 1,5 МБ, — дважды вставляли их в страницу и дважды
пересоздавали полоску загрузки, она начинала бег заново.

Держит, на родителе с адреса тестового калькулятора и кадре базы (оба адреса
подменены, база данных — заглушка с задержкой сети и учебными уроками):
  • уроки запрошены из базы один раз;
  • полоска загрузки — тот же элемент от первого кадра до главной;
  • главная открылась со всеми разделами.

Проверено возвращением дефекта: на прежней странице уроки запрошены дважды,
полоска пересоздана.

Запуск: python3 scratchpad/probes/check_kb_single_load.py (из корня репозитория).
"""
import json, os, pathlib, sys, time
from playwright.sync_api import sync_playwright
КБ = pathlib.Path(os.environ.get('BM_KB') or '/home/user/knowledge-baniamsk'); ЗАДЕРЖКА = 1200
def тело(ид, н):
    return (f'<div id="{ид}" style="display:none;"><h2><span class="lang-ru">Урок {н}</span><span class="lang-en">Lesson {н}</span></h2>'
            + '<p><span class="lang-ru">' + 'Учебный текст урока. ' * 400 + '</span><span class="lang-en">' + 'Sample lesson text. ' * 400 + '</span></p></div>')
уроки = [dict(id=f'lesson-{б}-{о}', block=б, ord=о, status='ready', title_ru=f'Урок {б}.{о}', title_en='L', nav_ru=f'Урок {б}.{о}', nav_en='L',
              short_ru='', short_en='', sub_ru='', sub_en='', body_html=тело(f'lesson-{б}-{о}', f'{б}.{о}')) for б, о in [(1,1),(2,1),(3,1),(3,2),(3,12),(5,1)]]
БЛОКИ = [dict(id='b%d'%н, num=н, ord=н, name_ru=['Компания','Продукт','Продажи','Конкуренты','Для клиентов'][н-1], name_en='B', sub_ru='', sub_en='') for н in (1,2,3,4,5)]
ЗАГЛ = """
window.__уроки = %s; window.__блоки = %s; const _зд = %d;
const _сессия = { user: { id: 'u1', email: 'm@baniamsk.ru' }, access_token: 't' };
const _ждать = (мс, з) => new Promise(r => setTimeout(() => r(з), мс));
window.__вызовы = { уроки: 0, дом: 0 };
Object.defineProperty(window, 'supabase', { configurable: true, get() { return { createClient: () => ({
  auth: { getSession: () => _ждать(150, { data: { session: _сессия } }), onAuthStateChange: () => ({ data: { subscription: { unsubscribe(){} } } }),
    signInWithPassword: async () => ({ data: { session: _сессия }, error: null }), setSession: () => _ждать(150, { data: { session: _сессия }, error: null }), signOut: async () => ({}) },
  from: (имя) => {
    if (имя === 'kb_lessons') window.__вызовы.уроки++;
    const данные = имя === 'kb_lessons' ? window.__уроки : имя === 'kb_blocks' ? window.__блоки
                 : имя === 'profiles' ? [{ id:'u1', email:'m@baniamsk.ru', full_name:'Проба', role:'manager' }] : [];
    const мс = имя === 'kb_lessons' ? _зд + (window.__вызовы.уроки - 1) * 1200 : 150;
    const цепь = { select: () => цепь, order: () => цепь, eq: () => цепь, is: () => цепь,
      maybeSingle: () => _ждать(мс, { data: данные[0] || null, error: null }), single: () => _ждать(мс, { data: данные[0] || null, error: null }),
      then: (ф, о) => _ждать(мс, { data: данные, error: null }).then(ф, о) };
    return { select: () => цепь, upsert: async () => ({ error: null }), update: () => цепь, insert: async () => ({ error: null }) };
  } }) }; }, set(v) {} });
""" % (json.dumps(уроки, ensure_ascii=False), json.dumps(БЛОКИ, ensure_ascii=False), ЗАДЕРЖКА)
РОДИТЕЛЬ = """<!doctype html><html><head><meta charset="utf-8"></head><body style="margin:0;background:#888">
<div id="ov" style="position:fixed;inset:0;padding:12px 0 0;overflow:hidden"><div style="height:calc(100dvh - 12px);display:flex;flex-direction:column;position:relative;background:#f0f6f6;border-radius:16px 16px 0 0;overflow:hidden">
<div id="ld" style="position:absolute;inset:0;background:#f0f6f6;display:flex;align-items:center;justify-content:center;z-index:2;transition:opacity .25s">База знаний загружается…</div>
<iframe id="f" style="border:0;flex:1;min-height:0" src="https://knowledge.baniamsk.ru/?embed=1"></iframe></div></div>
<script>addEventListener("message", e => { window.__пинг = (window.__пинг||0) + 1; if (e.data === "kbReady") { const w = document.getElementById('f').contentWindow, o = 'https://knowledge.baniamsk.ru';
  w.postMessage({type:'theme', dark:false}, o); w.postMessage({type:'tone', shift:0, sat:1, name:'bmsk'}, o);
  w.postMessage({type:'auth', user:{id:'u1', email:'m@baniamsk.ru', full_name:'Проба', role:'manager', access_token:'t'}}, o);
  const л = document.getElementById('ld'); л.style.opacity = '0'; setTimeout(() => л.style.display = 'none', 300); } });</script></body></html>"""
ШРИФТЫ = pathlib.Path('/home/user/-calculator-test/scratchpad/probes/шрифты_google.css').read_text(encoding='utf-8')
def кб(route):
    путь = route.request.url.split('knowledge.baniamsk.ru/', 1)[1].split('?')[0] or 'index.html'
    ф = КБ / путь
    if ф.is_file(): route.fulfill(status=200, body=ф.read_bytes(), content_type='text/html' if путь.endswith('.html') else None)
    else: route.fulfill(status=404, body='')
СОСТ = """() => { const d = document; const пл = d.querySelector('#loadingState .kb-load'); if (пл && !пл.__метка) пл.__метка = ++window.__полосок || (window.__полосок = 1); const в = э => !!э && э.getClientRects().length > 0 && getComputedStyle(э).visibility !== 'hidden';
  return [в(d.getElementById('loadingState')) ? 'загрузка' : '', в(d.getElementById('homeScreen')) ? 'главная' + d.querySelectorAll('#hsList > *').length : '',
          в(d.getElementById('authOverlay')) && d.getElementById('authOverlay').classList.contains('on') ? 'вход' : '',
          getComputedStyle(d.body).backgroundColor, window.__вызовы ? 'уроки' + window.__вызовы.уроки : ''].filter(Boolean).join(' '); }"""
with sync_playwright() as pw:
    бр = pw.chromium.launch(executable_path=os.environ.get('BM_CHROMIUM') or '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', args=['--no-sandbox'])
    стр = бр.new_page(viewport={'width': 390, 'height': 844}, device_scale_factor=1, color_scheme='dark')
    стр.route('https://test.calculator.baniamsk.ru/**', lambda r: r.fulfill(status=200, content_type='text/html', body=РОДИТЕЛЬ))
    стр.route('https://knowledge.baniamsk.ru/**', кб)
    стр.route('**/fonts.googleapis.com/**', lambda r: r.fulfill(status=200, content_type='text/css', body=ШРИФТЫ))
    стр.route('**/cdn.jsdelivr.net/**', lambda r: r.fulfill(status=200, content_type='application/javascript', body=''))
    стр.add_init_script(ЗАГЛ)
    стр.add_init_script("""(() => { const пер = () => { if (typeof showHomeScreen === 'function' && !showHomeScreen.__обёрнут) { const с = showHomeScreen;
      window.showHomeScreen = function() { window.__вызовы && window.__вызовы.дом++; return с.apply(this, arguments); }; window.showHomeScreen.__обёрнут = 1; } };
      document.addEventListener('DOMContentLoaded', пер); })();""")
    т0 = time.time(); стр.goto('https://test.calculator.baniamsk.ru/p.html', wait_until='commit')
    прошлое, лента, н = None, [], 0
    while time.time() - т0 < ЗАДЕРЖКА / 1000 + 4:
        try:
            к = стр.frames[1] if len(стр.frames) > 1 else None
            с = к.evaluate(СОСТ) if к else 'кадра нет'
        except Exception as e: с = 'ошибка ' + str(e)[:40]
        if с != прошлое: лента.append(f'{int((time.time()-т0)*1000):5d} мс  {с}'); прошлое = с
        н += 1; стр.wait_for_timeout(40)
    к = стр.frames[1]
    в = к.evaluate("() => ({ уроки: window.__вызовы.уроки, полосок: window.__полосок || 0, разделов: document.querySelectorAll('#hsList > *').length, главная: document.getElementById('homeScreen').getClientRects().length > 0 })")
    бр.close()
зам = []
if в['уроки'] != 1: зам.append(f"уроки запрошены из базы {в['уроки']} раз, а не один")
if в['полосок'] > 1: зам.append(f"полоска загрузки пересоздана: элементов {в['полосок']}")
if not (в['главная'] and в['разделов'] == 5): зам.append(f"главная не открылась со всеми разделами: {в}")
print('\n'.join(лента)); print(в)
print('\n'.join('ЗАМЕЧАНИЕ: ' + з for з in зам) if зам else 'Чисто: уроки загружены один раз, полоска загрузки не перезапускалась, главная открыта.')
sys.exit(1 if зам else 0)
