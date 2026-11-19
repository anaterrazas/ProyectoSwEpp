"""Regresiones: DB en memoria, multimedia temporal, salidas solo en este experimento."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from uuid import uuid4

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[4]


def main():
    target=BASE/'output'/'tests'/uuid4().hex;target.mkdir(parents=True)
    commands=[
        ('manual', BASE, ['-m','unittest','test_manual','-v']),
        ('capture',BASE.parents[1]/'tools',['-m','unittest','test_capture_dataset','test_video_dataset','-v']),
        ('individual',BASE.parent/'individual_v001',['-m','unittest','test_individual','-v']),
        ('prototype',BASE.parent/'day1_v001',['-m','unittest','test_prototype','-v']),
    ]
    django_code='''import os,tempfile,django
os.environ['DJANGO_SETTINGS_MODULE']='config.settings'
from django.conf import settings
settings.DATABASES={'default':{'ENGINE':'django.db.backends.sqlite3','NAME':':memory:'}}
settings.MIGRATION_MODULES={name:None for name in ('auth','admin','contenttypes','sessions','produccion','administracion','seguridad','monitoreo','reportes')}
with tempfile.TemporaryDirectory(prefix='epp_manual_regressions_') as media:
 settings.MEDIA_ROOT=media
 django.setup()
 from django.core.management import call_command
 call_command('check')
 from django.test.runner import DiscoverRunner
 failures=DiscoverRunner(verbosity=1).run_tests(['produccion','ml.calidad_botellas'])
 raise SystemExit(bool(failures))
'''
    commands.append(('project',ROOT,['-c',django_code]))
    results={};env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8')
    for name,cwd,args in commands:
        run=subprocess.run([sys.executable,'-B',*args],cwd=cwd,env=env,capture_output=True,timeout=600)
        output=run.stdout.decode('utf-8',errors='replace')+run.stderr.decode('utf-8',errors='replace')
        (target/(name+'.log')).write_text(output,encoding='utf-8')
        match=re.search(r'Ran (\d+) tests? in ([\d.]+)s',output)
        results[name]={'exit_code':run.returncode,'tests_run':int(match[1]) if match else None,'seconds':float(match[2]) if match else None,'log':str(target/(name+'.log'))}
        print(name,json.dumps(results[name]),flush=True)
    results['total_tests_run']=sum(v['tests_run'] or 0 for v in results.values())
    results['all_passed']=all(v['exit_code']==0 for v in results.values() if isinstance(v,dict))
    (target/'results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(str(target/'results.json'),flush=True)
    return 0 if results['all_passed'] else 1


if __name__=='__main__':raise SystemExit(main())
