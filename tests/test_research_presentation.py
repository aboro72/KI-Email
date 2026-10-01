import json
from types import SimpleNamespace

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.research_presentation import present_research, text_blocks


def test_existing_notes_and_product_cards():
    notes = 'Automatische KI-Recherche.\n\nEin kleiner Betrieb.\n\nProdukt-Fit:\n- AboroDesk: 70/100\n\nBeobachtungen:\n- Kundenanfragen\n- Wartung\n\nGesprächshypothese:\nAufgaben besser ordnen.'
    view = present_research(notes, json.dumps([{'label': 'AboroDesk', 'score': 70, 'matches': ['Kundenanfragen']}]))
    assert [s['title'] for s in view['sections']] == ['Zusammenfassung und Notizen', 'Beobachtungen', 'Gesprächshypothese']
    assert '<li>Kundenanfragen</li>' in view['sections'][1]['html']
    assert view['fits'][0]['priority'] == 'Sehr gute Passung'


def test_malformed_fit_keeps_text_and_empty_notes():
    view = present_research('Produkt-Fit:\n- AboroDesk: 30/100', '{broken')
    assert not view['fits']
    assert 'AboroDesk' in view['sections'][0]['html']
    assert present_research(None, None) == {'sections': [], 'fits': []}
    assert not present_research('Notiz', '{"score": 12}')['fits']


def test_simple_markdown_without_active_html():
    rendered = str(text_blocks('### Ergebnis\n\n**Wichtig** und `Beispiel`\n\n- A\n- B\n\n<script>alert(1)</script><img src=x onerror=alert(2)>'))
    assert '<h4>Ergebnis</h4>' in rendered
    assert '<strong>Wichtig</strong>' in rendered
    assert '<code>Beispiel</code>' in rendered
    assert '<ul><li>A</li><li>B</li></ul>' in rendered
    assert '<script>' not in rendered and '<img' not in rendered
    assert '&lt;script&gt;' in rendered


def test_bad_scores_and_matches():
    data = [None, {'score': 'bad'}, {'label': 'A', 'score': 200, 'matches': 'not a list'}, {'label': 'B', 'score': -1, 'matches': [None, 'Text']}]
    fits = present_research('', json.dumps(data))['fits']
    assert [fit['score'] for fit in fits] == [100, 0]
    assert fits[0]['matches'] == [] and fits[1]['matches'] == ['Text']


def test_markdown_sections():
    view = present_research('## Zusammenfassung\nText\n\n**Beobachtungen:**\n* Hinweis\n\n## Gesprächshypothese\nFrage', '[]')
    assert [s['title'] for s in view['sections']] == ['Zusammenfassung', 'Beobachtungen', 'Gesprächshypothese']


def test_template_escapes_cards_and_renders_structure():
    env = Environment(loader=FileSystemLoader('app/templates'), autoescape=select_autoescape())
    company = SimpleNamespace(id=1, name='Firma', domain='firma.de', industry='Handwerk', research_status='completed', website='', researched_at=None, research_error='')
    view = present_research('Beobachtungen:\n- **Kundenanfragen**', json.dumps([{'label': '<script>bad</script>', 'score': 20, 'matches': ['<img src=x>']}]))
    html = env.get_template('crm_company_detail.html').render(company=company, research=view, contacts=[], leads=[], activities=[], users=[])
    assert '<strong>Kundenanfragen</strong>' in html
    assert '<script>bad</script>' not in html
    assert '&lt;script&gt;bad&lt;/script&gt;' in html
    assert 'research-product' in html and 'Recherche abgeschlossen' in html
