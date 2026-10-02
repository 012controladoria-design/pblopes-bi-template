#!/usr/bin/env python3
"""Aplica o tema claro/escuro nas telas do relatório Financeiro P B Lopes.

Pode rodar quantas vezes quiser (é idempotente): antes de criar, apaga o que
uma rodada anterior criou. Rode na raiz do repositório:

    python3 scripts/aplicar_tema.py

O que faz em cada tela visível (menos a "Página 2", vazia):
  1. Cria, ocultos, o fundo claro (imagem da página inteira), a logo colorida
     por cima da logo branca e uma cópia azul de cada título (caixa de texto).
  2. Cria uma segmentação oculta em dTema[Tema], começando em "Escuro".
  3. Cria o botão ☀ (vai para o claro) e o botão ☾ (volta para o escuro).
  4. Cria dois indicadores por tela que trocam o que aparece e a seleção da
     segmentação oculta.
  5. Troca as letras brancas que ficam direto sobre o fundo pela medida
     [Tema Cor Texto] (fx). Matrizes com fundo transparente ganham um painel
     azul Scania, para as letras brancas continuarem legíveis nos dois temas.
"""
import copy
import glob
import hashlib
import json
import os

REPORT = 'Financeiro P B Lopes.Report'
DEF = f'{REPORT}/definition'
PAGES_DIR = f'{DEF}/pages'
BOOKMARKS_DIR = f'{DEF}/bookmarks'
VC_SCHEMA = 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.12.0/schema.json'
BM_SCHEMA = 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/bookmark/2.1.0/schema.json'

FUNDO_CLARO = 'Fundo_Tema_Claro7310452896314507.jpg'
LOGO_COLORIDA = 'PBLopes_Scania_colorido6903853022629551.png'
AZUL_SCANIA = '#041E42'
PREFIXO = 'tema'                 # nome dos visuais criados por este script
PREFIXO_BM = 'BookmarkTema'      # nome dos indicadores criados por este script
GRUPO_BM = 'BookmarkGroupTemaClaroEscuro'

# propriedades de cor de LETRA; as de fundo, borda e preenchimento ficam como estão
FONTE = {'fontColor', 'labelColor', 'color', 'titleColor', 'fontColorPrimary', 'fontColorSecondary'}
OBJETOS_FORA = {'background', 'border', 'fill', 'dataPoint', 'items', 'general', 'outline'}
TIPOS_SEM_FX = {'actionButton', 'image', 'textbox', 'shape', 'basicShape'}
TABELAS = {'pivotTable', 'tableEx'}


def L(v):
    return {'expr': {'Literal': {'Value': v}}}


def cor(h):
    return {'solid': {'color': L(f"'{h}'")}}


FX_TEXTO = {'solid': {'color': {'expr': {'Measure': {'Expression': {'SourceRef': {'Entity': '_Medidas'}},
                                                     'Property': 'Tema Cor Texto'}}}}}


def nome(*partes, n=16):
    return PREFIXO + hashlib.sha1('|'.join(partes).encode()).hexdigest()[:n]


def load(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def save(p, d):
    """Grava mantendo a quebra de linha do arquivo original (o report.json usa CRLF)."""
    os.makedirs(os.path.dirname(p), exist_ok=True)
    crlf = os.path.exists(p) and b'\r\n' in open(p, 'rb').read()
    texto = json.dumps(d, ensure_ascii=False, indent=2)
    with open(p, 'wb') as f:
        f.write((texto.replace('\n', '\r\n') if crlf else texto).encode('utf-8'))


def eh_branco(c):
    if not isinstance(c, dict) or 'solid' not in c:
        return False
    e = c['solid'].get('color', {}).get('expr', {})
    if e.get('ThemeDataColor') == {'ColorId': 0, 'Percent': 0}:
        return True
    v = e.get('Literal', {}).get('Value', '')
    return v.lower() in ("'#fff'", "'#ffffff'")


def fundo_ligado(vis):
    bg = vis.get('visualContainerObjects', {}).get('background', [{}])[0].get('properties', {})
    return bool(bg) and bg.get('show') != L('false')


def filtro_tema(valor):
    return {'Version': 2, 'From': [{'Name': 't', 'Entity': 'dTema', 'Type': 0}],
            'Where': [{'Condition': {'In': {
                'Expressions': [{'Column': {'Expression': {'SourceRef': {'Source': 't'}}, 'Property': 'Tema'}}],
                'Values': [[{'Literal': {'Value': f"'{valor}'"}}]]}}}]}


def botao(nm, pos, simbolo, fundo, fundo_hover, letra, bookmark, dica, oculto):
    padrao = {'id': 'default'}
    d = {
        '$schema': VC_SCHEMA, 'name': nm, 'position': pos,
        'visual': {
            'visualType': 'actionButton',
            'objects': {
                'icon': [{'properties': {'show': L('false')}},
                         {'properties': {'shapeType': L("'blank'"), 'show': L('false')}, 'selector': padrao}],
                'text': [{'properties': {'show': L('true')}},
                         {'properties': {'show': L('true'), 'text': L(f"'{simbolo}'"), 'fontColor': cor(letra),
                                         'fontSize': L('15D'), 'bold': L('true'),
                                         'horizontalAlignment': L("'center'"), 'verticalAlignment': L("'middle'")},
                          'selector': padrao},
                         {'properties': {'text': L(f"'{simbolo}'"), 'fontColor': cor(letra)}, 'selector': {'id': 'hover'}}],
                'fill': [{'properties': {'show': L('true')}},
                         {'properties': {'show': L('true'), 'fillColor': cor(fundo), 'transparency': L('0D')}, 'selector': padrao},
                         {'properties': {'fillColor': cor(fundo_hover), 'transparency': L('0D')}, 'selector': {'id': 'hover'}}],
                'outline': [{'properties': {'show': L('false')}}],
            },
            'visualContainerObjects': {
                'background': [{'properties': {'show': L('false')}}],
                'title': [{'properties': {'show': L('false')}}],
                'visualLink': [{'properties': {'show': L('true'), 'type': L("'Bookmark'"),
                                               'bookmark': L(f"'{bookmark}'"), 'tooltip': L(f"'{dica}'")}}],
                'border': [{'properties': {'show': L('false'), 'radius': L('15D')}}],
                'general': [{'properties': {'keepLayerOrder': L('true')}}],
            },
            'drillFilterOtherVisuals': True,
        },
        'howCreated': 'InsertVisualButton',
    }
    if oculto:
        d['isHidden'] = True
    return d


def lugar_do_botao(vis_visiveis, textos, w=40, h=30):
    """Espaço livre no topo, o mais à direita possível. Sem espaço: ponta direita do título."""
    rects = [(v['position']['x'], v['position']['y'], v['position']['x'] + v['position']['width'],
              v['position']['y'] + v['position']['height']) for v in vis_visiveis]
    livres = [(x, y) for y in range(2, 100 - h, 2) for x in range(2, 1280 - w - 2, 2)
              if all(x + w + 3 <= a or x - 3 >= c or y + h + 3 <= b or y - 3 >= d for a, b, c, d in rects)]
    if livres:
        x, y = sorted(livres, key=lambda t: (-t[0], t[1]))[0]
        return x, y, None
    t = textos[0]['position']
    return int(t['x'] + t['width'] - w), int(t['y'] + (t['height'] - h) / 2), w + 8


def registrar_imagem(report):
    rr = [p for p in report['resourcePackages'] if p['name'] == 'RegisteredResources'][0]
    if not any(i['name'] == FUNDO_CLARO for i in rr['items']):
        rr['items'].append({'name': FUNDO_CLARO, 'path': FUNDO_CLARO, 'type': 'Image'})


def limpar_rodada_anterior(pid):
    for pasta in glob.glob(f'{PAGES_DIR}/{pid}/visuals/{PREFIXO}*'):
        for f in glob.glob(f'{pasta}/*'):
            os.remove(f)
        os.rmdir(pasta)


def aplicar_fx(vis, painel):
    """Troca letras brancas por [Tema Cor Texto]. Devolve quantas propriedades mudou."""
    n = 0
    vco = vis.setdefault('visualContainerObjects', {})
    if painel:
        vco['background'] = [{'properties': {'show': L('true'), 'color': cor(AZUL_SCANIA), 'transparency': L('10D')}}]
        return 0
    transparente = not fundo_ligado(vis)
    for e in vco.get('title', []):
        p = e.setdefault('properties', {})
        if transparente and p.get('show') != L('false') and ('fontColor' not in p or eh_branco(p['fontColor'])
                                                              or 'ThemeDataColor' in json.dumps(p['fontColor'])):
            p['fontColor'] = copy.deepcopy(FX_TEXTO)
            n += 1
    if vis['visualType'] in TABELAS:
        return n
    for obj, lst in vis.get('objects', {}).items():
        if obj in OBJETOS_FORA:
            continue
        for e in lst:
            p = e.get('properties', {})
            if any(k.startswith('back') for k in p):      # tem fundo próprio: a letra branca já é legível
                continue
            for k in list(p):
                if k in FONTE and eh_branco(p[k]):
                    p[k] = copy.deepcopy(FX_TEXTO)
                    n += 1
    return n


def main():
    report_path = f'{DEF}/report.json'
    report = load(report_path)
    registrar_imagem(report)
    save(report_path, report)

    # indicadores antigos deste script
    for f in glob.glob(f'{BOOKMARKS_DIR}/{PREFIXO_BM}*.bookmark.json'):
        os.remove(f)
    meta = load(f'{BOOKMARKS_DIR}/bookmarks.json')
    meta['items'] = [i for i in meta['items'] if i.get('name') != GRUPO_BM]
    filhos = []

    ordem = load(f'{PAGES_DIR}/pages.json')['pageOrder']
    resumo = []
    for pid in ordem:
        page = load(f'{PAGES_DIR}/{pid}/page.json')
        if page.get('visibility') == 'HiddenInViewMode' or page.get('type'):
            continue
        limpar_rodada_anterior(pid)
        vs = {}
        for f in glob.glob(f'{PAGES_DIR}/{pid}/visuals/*/visual.json'):
            v = load(f)
            vs[v['name']] = (f, v)
        if not vs:
            continue

        def oculto(v):
            if v.get('isHidden'):
                return True
            g = v.get('parentGroupName')
            while g:
                if vs[g][1].get('isHidden'):
                    return True
                g = vs[g][1].get('parentGroupName')
            return False

        def em_popup(v):
            g = v.get('parentGroupName')
            while g:
                if 'Pop' in vs[g][1].get('visualGroup', {}).get('displayName', ''):
                    return True
                g = vs[g][1].get('parentGroupName')
            return False

        normais = [(f, v) for f, v in vs.values() if 'visual' in v and not em_popup(v)]
        logos = [(f, v) for f, v in normais if v['visual']['visualType'] == 'image']
        titulos = [(f, v) for f, v in normais if v['visual']['visualType'] == 'textbox']
        visiveis = [v for f, v in normais if not oculto(v)]

        # 1. fx nas letras e painel nas matrizes transparentes
        mudou = 0
        for f, v in normais:
            vis = v['visual']
            t = vis['visualType']
            if t in TIPOS_SEM_FX:
                continue
            painel = False
            if t in TABELAS and not fundo_ligado(vis):
                letras = [p for o in ('values', 'columnHeaders', 'rowHeaders') for e in vis.get('objects', {}).get(o, [])
                          for p in [e.get('properties', {})] if not any(k.startswith('back') for k in p)
                          and any(eh_branco(p.get(k)) for k in FONTE)]
                painel = bool(letras)
            mudou += aplicar_fx(vis, painel)
            if v['position'].get('z', 0) <= 0:
                v['position']['z'] = 1
            save(f, v)
        for f, v in logos + titulos:
            if v['position'].get('z', 0) <= 0:
                v['position']['z'] = 1
                save(f, v)

        novos = []
        # 2. fundo claro
        n_fundo = nome(pid, 'fundo')
        novos.append({'$schema': VC_SCHEMA, 'name': n_fundo,
                      'position': {'x': 0, 'y': 0, 'z': 0, 'height': 720, 'width': 1280, 'tabOrder': 0},
                      'visual': {'visualType': 'image',
                                 'objects': {'general': [{'properties': {'imageUrl': {'expr': {'ResourcePackageItem': {
                                     'PackageName': 'RegisteredResources', 'PackageType': 1, 'ItemName': FUNDO_CLARO}}}}}]},
                                 'visualContainerObjects': {'general': [{'properties': {'keepLayerOrder': L('true')}}],
                                                            'visualHeader': [{'properties': {'show': L('false')}}],
                                                            'title': [{'properties': {'show': L('false')}}]},
                                 'drillFilterOtherVisuals': True},
                      'isHidden': True})
        # 3. logos coloridas e títulos azuis
        pares_logo, pares_titulo = [], []
        for f, v in logos:
            c = copy.deepcopy(v)
            c['name'] = nome(pid, 'logo', v['name'])
            c['visual']['objects']['general'][0]['properties']['imageUrl']['expr']['ResourcePackageItem']['ItemName'] = LOGO_COLORIDA
            c['isHidden'] = True
            c.pop('parentGroupName', None)
            novos.append(c)
            pares_logo.append((v['name'], c['name']))
        for f, v in titulos:
            c = copy.deepcopy(v)
            c['name'] = nome(pid, 'titulo', v['name'])
            for par in c['visual']['objects']['general'][0]['properties'].get('paragraphs', []):
                for run in par.get('textRuns', []):
                    run.setdefault('textStyle', {})['color'] = AZUL_SCANIA
            c['isHidden'] = True
            c.pop('parentGroupName', None)
            novos.append(c)
            pares_titulo.append((v['name'], c['name']))
        # 4. segmentação oculta do tema
        n_seg = nome(pid, 'segmentacao')
        novos.append({'$schema': VC_SCHEMA, 'name': n_seg,
                      'position': {'x': 0, 'y': 0, 'z': 2, 'height': 40, 'width': 120, 'tabOrder': 2},
                      'visual': {'visualType': 'slicer',
                                 'query': {'queryState': {'Values': {'projections': [{
                                     'field': {'Column': {'Expression': {'SourceRef': {'Entity': 'dTema'}}, 'Property': 'Tema'}},
                                     'queryRef': 'dTema.Tema', 'nativeQueryRef': 'Tema', 'active': True}]}}},
                                 'objects': {'data': [{'properties': {'mode': L("'Basic'")}}],
                                             'selection': [{'properties': {'singleSelect': L('true'),
                                                                           'selectAllCheckboxEnabled': L('false')}}],
                                             'general': [{'properties': {'filter': {'filter': filtro_tema('Escuro')}}}]},
                                 'visualContainerObjects': {'title': [{'properties': {'show': L('false')}}]},
                                 'drillFilterOtherVisuals': True},
                      'isHidden': True})
        # 5. botões
        bm_claro = PREFIXO_BM + hashlib.sha1(f'{pid}|claro'.encode()).hexdigest()[:12]
        bm_escuro = PREFIXO_BM + hashlib.sha1(f'{pid}|escuro'.encode()).hexdigest()[:12]
        x, y, encolher = lugar_do_botao(visiveis, [v for f, v in titulos])
        if encolher:      # sem espaço livre: o título (e a cópia azul) fica mais estreito
            for f, v in titulos[:1]:
                v['position']['width'] -= encolher
                save(f, v)
            for c in novos:
                if c['name'] == nome(pid, 'titulo', titulos[0][1]['name']):
                    c['position']['width'] -= encolher
        pos = {'x': x, 'y': y, 'z': 30000, 'height': 30, 'width': 40, 'tabOrder': 30000}
        n_bc = nome(pid, 'botao-claro')
        n_be = nome(pid, 'botao-escuro')
        novos.append(botao(n_bc, dict(pos), '☀', '#FFFFFF', '#DCE6F2', AZUL_SCANIA, bm_claro,
                           'Mudar para o tema claro (fundo branco, letras azuis)', oculto=False))
        novos.append(botao(n_be, dict(pos), '☾', AZUL_SCANIA, '#0B3A7A', '#FFFFFF', bm_escuro,
                           'Voltar para o tema escuro (fundo azul, letras brancas)', oculto=True))
        for c in novos:
            save(f"{PAGES_DIR}/{pid}/visuals/{c['name']}/visual.json", c)

        # 6. indicadores
        tipos = {c['name']: c['visual']['visualType'] for c in novos}
        tipos.update({v['name']: v['visual']['visualType'] for f, v in logos + titulos})
        so_claro = [n_fundo, n_be] + [b for a, b in pares_logo] + [b for a, b in pares_titulo]
        so_escuro = [n_bc] + [a for a, b in pares_logo] + [a for a, b in pares_titulo]

        def estado(tema, visiveis_tema, ocultos_tema):
            vc = {}
            for n in visiveis_tema:
                vc[n] = {'singleVisual': {'visualType': tipos[n]}}
            for n in ocultos_tema:
                vc[n] = {'singleVisual': {'visualType': tipos[n], 'display': {'mode': 'hidden'}}}
            vc[n_seg] = {'singleVisual': {'visualType': 'slicer', 'display': {'mode': 'hidden'},
                                          'objects': {'merge': {'general': [{'properties': {
                                              'filter': {'filter': filtro_tema(tema)}}}]}}}}
            return vc

        alvos = so_claro + so_escuro + [n_seg]
        for bm, tema, vis_t, ocu_t, rotulo in ((bm_claro, 'Claro', so_claro, so_escuro, 'claro'),
                                               (bm_escuro, 'Escuro', so_escuro, so_claro, 'escuro')):
            save(f'{BOOKMARKS_DIR}/{bm}.bookmark.json', {
                '$schema': BM_SCHEMA,
                'displayName': f"Tema {rotulo} · {page['displayName']}",
                'name': bm,
                'options': {'applyOnlyToTargetVisuals': True, 'targetVisualNames': alvos},
                'explorationState': {'version': '1.3', 'activeSection': pid,
                                     'sections': {pid: {'visualContainers': estado(tema, vis_t, ocu_t)}}},
            })
            filhos.append(bm)
        resumo.append((page['displayName'], mudou, len(logos), len(titulos), (x, y), bool(encolher)))

    meta['items'].append({'name': GRUPO_BM, 'displayName': 'Tema claro / escuro', 'children': filhos})
    save(f'{BOOKMARKS_DIR}/bookmarks.json', meta)
    for r in resumo:
        print('%-32s fx=%3d logos=%d títulos=%d botão=%s%s' % (r[0], r[1], r[2], r[3], r[4],
                                                               ' (título encolhido)' if r[5] else ''))


if __name__ == '__main__':
    main()
