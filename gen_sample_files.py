import os
import numpy as np
from demo_data import generate_demo_cu_series, generate_demo_czts_series

os.makedirs('sample_files', exist_ok=True)

# Generate Cu series files
cu_data = generate_demo_cu_series()
x = np.array(cu_data['x'])
for s in cu_data['samples']:
    fname = os.path.join('sample_files', f"Sample_{s['name']}.txt")
    y = np.array(s['y'])
    np.savetxt(fname, np.column_stack((x, y)), fmt='%.3f\t%.2f', header='2Theta\tIntensity', comments='')

for c in cu_data['pdf_cards']:
    safe_card_name = c['name'].replace('#', '_').replace(' ', '_')
    fname = os.path.join('sample_files', f"PDF_{safe_card_name}.txt")
    lines = ['2Theta\tI%']
    for p in c['peaks']:
        lines.append(f"{p['angle']:.3f}\t{p['intensity']:.1f}")
    with open(fname, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

# Generate CZTS series files
czts_data = generate_demo_czts_series()
x2 = np.array(czts_data['x'])
for s in czts_data['samples']:
    safe_name = s['name'].replace('℃', 'C').replace('/', '_').replace(' ', '_').replace('(', '').replace(')', '')
    fname = os.path.join('sample_files', f"Sample_{safe_name}.txt")
    y = np.array(s['y'])
    np.savetxt(fname, np.column_stack((x2, y)), fmt='%.3f\t%.2f', header='2Theta\tIntensity', comments='')

for c in czts_data['pdf_cards']:
    safe_card_name = c['name'].replace('#', '_').replace(' ', '_')
    fname = os.path.join('sample_files', f"PDF_{safe_card_name}.txt")
    lines = ['2Theta\tI%']
    for p in c['peaks']:
        lines.append(f"{p['angle']:.3f}\t{p['intensity']:.1f}")
    with open(fname, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

print("Created sample files:", os.listdir('sample_files'))
