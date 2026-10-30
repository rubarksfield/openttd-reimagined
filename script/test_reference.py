#!/usr/bin/env python3
"""Run unchanged upstream expectations with locally scoped resource discovery."""
from pathlib import Path
import subprocess,json,time
ROOT=Path(__file__).resolve().parents[1];cmake=ROOT/'.tools/python/bin/cmake'
reference=Path(subprocess.check_output(['python3',str(ROOT/'script/prepare_upstream.py'),'--reference'],text=True).strip())
subprocess.run(['python3',str(ROOT/'script/prepare_graphics.py')],check=True)
with (ROOT/'evidence/reference-unit-tests.log').open('w') as log:
    subprocess.run([str(ROOT/'.tools/python/bin/ctest'),'--test-dir',str(ROOT/'build/reference'),'--output-on-failure','-E','^regression_','--timeout','30'],stdout=log,stderr=subprocess.STDOUT,check=True)
subprocess.run([str(cmake),'--build',str(ROOT/'build/reference'),'--target','regression_files','--parallel','2'],check=True)
results=[]
for name in ['regression','stationlist']:
    cmd=[str(cmake),'-DOPENTTD_EXECUTABLE='+str(ROOT/'script/reference_test_launcher.sh'),'-DREGRESSION_TEST='+name,'-P',str(reference/'cmake/scripts/Regression.cmake')]
    start=time.monotonic();r=subprocess.run(cmd,cwd=ROOT/'build/reference',text=True,capture_output=True,timeout=45)
    record={'name':name,'command':cmd,'exit_code':r.returncode,'seconds':time.monotonic()-start,'stdout':r.stdout,'stderr':r.stderr,'expected_results_modified':False,'launch_difference':'-X local search; explicit OpenGFX, NoSound and NoMusic'}
    (ROOT/'evidence'/f'upstream-regression-{name}.json').write_text(json.dumps(record,indent=2));results.append(record)
    if r.returncode:raise RuntimeError(f'{name}: {r.stdout}\n{r.stderr}')
    print(f'Original {name} expectations: PASS')
(ROOT/'evidence/upstream-regression-summary.json').write_text(json.dumps(results,indent=2))
subprocess.run(['python3',str(ROOT/'script/smoke_reference.py')],check=True)
