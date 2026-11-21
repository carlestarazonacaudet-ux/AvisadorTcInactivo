"""Pruebas del intervalo de alarma y de las escalas V19, sin requerir interfaz gráfica."""
import ast
import pathlib
import unittest

src=(pathlib.Path(__file__).parents[1]/'avisador_v24.py').read_text(encoding='utf-8')
module=ast.parse(src)
selected=[]
for item in module.body:
    if isinstance(item,ast.FunctionDef) and item.name in ('audio_repeat_due','scaled_font'):
        selected.append(item)
    if isinstance(item,ast.Assign) and any(isinstance(target,ast.Name) and target.id=='DEFAULTS' for target in item.targets):
        selected.append(item)
namespace={}
exec(compile(ast.Module(body=selected,type_ignores=[]),'<v19_settings>','exec'),namespace)

class TestAudioRepeat(unittest.TestCase):
    def test_first_and_subsequent_sounds(self):
        due=namespace['audio_repeat_due']
        self.assertTrue(due(500,None,10))
        self.assertFalse(due(505,500,10))
        self.assertFalse(due(509,500,10))
        self.assertTrue(due(510,500,10))
        self.assertTrue(due(620,500,10))
    def test_pause_or_unreadable_clock(self):
        due=namespace['audio_repeat_due']
        self.assertFalse(due(None,500,2))
        self.assertFalse(due(505,505,1))
        self.assertTrue(due(0,500,2))
    def test_one_second_option(self):
        due=namespace['audio_repeat_due']
        self.assertFalse(due(100,100,1))
        self.assertTrue(due(101,100,1))

class TestScales(unittest.TestCase):
    def test_text_size_clamps(self):
        size=namespace['scaled_font']
        self.assertEqual(size(10,100),10)
        self.assertEqual(size(10,50),7)  # mínimo legible
        self.assertEqual(size(28,150),42)
        self.assertEqual(size(28,180),50)
    def test_all_new_settings_have_defaults(self):
        defaults=namespace['DEFAULTS']
        self.assertEqual(defaults['repeticion'],6)
        for field in ('visual_escala','idle_total_escala','edades_escala','controles_escala'):
            self.assertEqual(defaults[field],100)

if __name__=='__main__': unittest.main()
