"""
app.py - XRD-Plotter 本地服务主程序
"""
import io
import os
import json
import base64
import urllib.parse
import numpy as np
from scipy.signal import find_peaks, savgol_filter
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
from demo_data import generate_demo_cu_series, generate_demo_czts_series
from plotter import parse_xrd_text, parse_pdf_card_text, render_xrd_plot

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024 * 1024  # 最大 64MB 上传
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # 禁用静态文件缓存方便实时微调

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLE_DIR = os.path.join(BASE_DIR, 'sample_files')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/demo/<demo_type>')
def get_demo(demo_type):
    """获取演示数据"""
    if demo_type == 'cu':
        data = generate_demo_cu_series()
        for s in data['samples']:
            s['x'] = data['x']
        return jsonify({"success": True, "data": data})
    elif demo_type == 'czts':
        data = generate_demo_czts_series()
        for s in data['samples']:
            s['x'] = data['x']
        return jsonify({"success": True, "data": data})
    else:
        return jsonify({"success": False, "error": "Unknown demo type"}), 400

@app.route('/api/upload/xrd', methods=['POST'])
def upload_xrd():
    """解析上传的 XRD 实测文本数据文件"""
    if 'files' not in request.files:
        return jsonify({"success": False, "error": "没有上传文件"}), 400
        
    uploaded_files = request.files.getlist('files')
    parsed_samples = []
    
    # 常用学术配色板
    default_colors = ['#1f77b4', '#c0392b', '#2c3e50', '#008b8b', '#b8860b', '#8e44ad', '#27ae60', '#d35400']
    
    for i, file in enumerate(uploaded_files):
        filename = file.filename
        content_bytes = file.read()
        
        # 尝试不同字符编码解码
        decoded_text = None
        for enc in ['utf-8', 'gbk', 'gb2312', 'utf-16', 'latin1']:
            try:
                decoded_text = content_bytes.decode(enc)
                break
            except Exception:
                continue
                
        if not decoded_text:
            continue
            
        try:
            x, y = parse_xrd_text(decoded_text)
            sample_name = os.path.splitext(filename)[0]
            # 简化样品名称
            sample_name = sample_name.replace('Sample_', '').replace('_', ' ')
            parsed_samples.append({
                "id": f"sample_{os.urandom(4).hex()}",
                "name": sample_name,
                "color": default_colors[i % len(default_colors)],
                "x": x,
                "y": y,
                "label_pos": "right"
            })
        except Exception as e:
            return jsonify({"success": False, "error": f"文件 {filename} 解析失败: {str(e)}"}), 400
            
    return jsonify({"success": True, "samples": parsed_samples})

@app.route('/api/upload/pdf', methods=['POST'])
def upload_pdf_card():
    """解析上传的 PDF 标准卡片文件 (支持单个或批量多选上传)"""
    files = request.files.getlist('files')
    if not files and 'file' in request.files:
        files = [request.files['file']]
    if not files:
        return jsonify({"success": False, "error": "没有上传卡片文件"}), 400
        
    card_colors = ['#cc0000', '#1e90ff', '#800080', '#228b22', '#ff8c00', '#008b8b']
    parsed_cards = []
    
    for i, file in enumerate(files):
        filename = file.filename
        content_bytes = file.read()
        
        decoded_text = None
        for enc in ['utf-8', 'gbk', 'gb2312', 'utf-16', 'latin1']:
            try:
                decoded_text = content_bytes.decode(enc)
                break
            except Exception:
                continue
                
        if not decoded_text:
            continue
            
        try:
            peaks = parse_pdf_card_text(decoded_text)
            card_name = os.path.splitext(filename)[0].replace('PDF_', '').replace('_', ' ')
            parsed_cards.append({
                "id": f"card_{os.urandom(4).hex()}",
                "name": card_name,
                "color": card_colors[i % len(card_colors)],
                "peaks": peaks
            })
        except Exception as e:
            return jsonify({"success": False, "error": f"卡片 {filename} 解析失败: {str(e)}"}), 400
            
    return jsonify({"success": True, "cards": parsed_cards})

@app.route('/api/plot', methods=['POST'])
def plot_endpoint():
    """接收参数配置，生成预览图像"""
    try:
        config = request.get_json(force=True)
        img_bytes, mimetype = render_xrd_plot(config, output_format='png', dpi=150)
        b64 = base64.b64encode(img_bytes).decode('utf-8')
        return jsonify({
            "success": True,
            "image": f"data:{mimetype};base64,{b64}"
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/auto_peaks', methods=['POST'])
def auto_detect_peaks():
    """智能自动找峰：识别顶层样品的物理极大值，并从左到右依次赋予不同学术符号与颜色"""
    from scipy.signal import find_peaks
    import numpy as np
    
    data = request.get_json(force=True)
    samples = data.get('samples', [])
    if not samples:
        return jsonify({"success": False, "error": "当前没有样品数据"}), 400
        
    settings = data.get('settings', {})
    x_min = float(settings.get('x_min', 10))
    x_max = float(settings.get('x_max', 80))
    
    # 支持选择在哪个样品上找峰 (默认 top 最顶层)
    target_sample_id = data.get('target_sample_id', 'top')
    chosen_sample = samples[-1]
    if target_sample_id != 'top':
        for s in samples:
            if s.get('id') == target_sample_id or s.get('name') == target_sample_id:
                chosen_sample = s
                break
                
    x_raw = chosen_sample.get('x') if 'x' in chosen_sample else data.get('x')
    y_raw = chosen_sample.get('y')
    if x_raw is None or y_raw is None:
        return jsonify({"success": False, "error": "样品缺少坐标数据"}), 400
    x = np.array(x_raw)
    y = np.array(y_raw)
    
    # 筛选当前可视范围
    mask = (x >= x_min) & (x <= x_max)
    if not np.any(mask):
        return jsonify({"success": False, "error": "当前可视角度范围内无数据"}), 400
        
    x_sub = x[mask]
    y_sub = y[mask]
    
    # 平滑去噪后再进行物理特征峰识别，避免仪器毛刺假峰干扰
    settings = data.get('settings', {})
    smooth_w = int(settings.get('smooth_window', 0))
    w = smooth_w if smooth_w >= 3 else 7
    if w % 2 == 0:
        w += 1
    if len(y_sub) > w:
        try:
            y_clean = savgol_filter(y_sub, window_length=w, polyorder=2 if w >= 5 else 1)
        except Exception:
            y_clean = y_sub
    else:
        y_clean = y_sub

    # 归一化
    y_min, y_max = np.min(y_clean), np.max(y_clean)
    if y_max > y_min:
        norm_y = (y_clean - y_min) / (y_max - y_min)
    else:
        norm_y = np.zeros_like(y_clean)
        
    # 可调节灵敏度 prominence 和最小间距 distance
    prominence = float(data.get('prominence', 0.035))
    distance = int(data.get('distance', 8))
    
    peaks, _ = find_peaks(norm_y, prominence=prominence, distance=distance)
    if len(peaks) == 0:
        peaks, _ = find_peaks(norm_y, prominence=prominence * 0.5, distance=max(3, distance // 2))
        
    detected_angles = x_sub[peaks]
    
    # 国际学术规范标记循环 (从左到右依次使用不同图标)
    marker_cycle = ['diamond', 'triangle_up', 'circle', 'square', 'triangle_down', 'cross', 'star', 'plus']
    color_cycle = ['#c0392b', '#1f77b4', '#228b22', '#2c3e50', '#8e44ad', '#d35400', '#008b8b', '#c71585']
    
    target_val = chosen_sample.get('id', 'top')
    if chosen_sample == samples[-1]:
        target_val = 'top'

    new_annotations = []
    for i, ang in enumerate(detected_angles):
        m_idx = i % len(marker_cycle)
        new_annotations.append({
            "angle": round(float(ang), 2),
            "text": "", # 晶面留给用户自定义填写
            "marker": marker_cycle[m_idx],
            "target": target_val,
            "color": color_cycle[m_idx],
            "vertical": True
        })
        
    return jsonify({
        "success": True,
        "sample_name": chosen_sample.get('name', 'Sample'),
        "annotations": new_annotations,
        "count": len(new_annotations)
    })

@app.route('/api/snap_angles', methods=['POST'])
def snap_angles_endpoint():
    """将现有所有标注的角度，一键校准吸附到其所在样品的真实物理峰尖精确值"""
    data = request.get_json(force=True)
    samples = data.get('samples', [])
    annotations = data.get('annotations', [])
    if not samples or not annotations:
        return jsonify({"success": True, "annotations": annotations})
        
    # 构建样品字典
    sample_map = {}
    for s_idx, s in enumerate(samples):
        sid = s.get('id', f'sample_{s_idx}')
        sample_map[sid] = s
        sample_map[f'idx_{s_idx}'] = s
        if s.get('name'):
            sample_map[s.get('name')] = s
    sample_map['top'] = samples[-1]
    
    corrected = []
    for ann in annotations:
        target = ann.get('target', 'top')
        s = sample_map.get(target, samples[-1])
        x = np.array(s.get('x', []))
        y = np.array(s.get('y', []))
        
        orig_angle = float(ann.get('angle', 0))
        if len(x) > 0 and len(y) == len(x):
            # 在 ±1.5° 搜索真实峰顶
            win = (x >= orig_angle - 1.5) & (x <= orig_angle + 1.5)
            if np.any(win):
                apex_idx = np.where(win)[0][np.argmax(y[win])]
                ann_copy = dict(ann)
                ann_copy['angle'] = round(float(x[apex_idx]), 2)
                corrected.append(ann_copy)
                continue
        corrected.append(ann)
        
    return jsonify({"success": True, "annotations": corrected})

@app.route('/api/export', methods=['POST'])
def export_endpoint():
    """高分辨率导出下载接口 (PNG 300/600 DPI, SVG, PDF)"""
    try:
        config = request.get_json(force=True)
        export_format = config.get('export_format', 'png_300')
        
        if export_format == 'svg':
            data_bytes, mimetype = render_xrd_plot(config, output_format='svg')
            ext = 'svg'
        elif export_format == 'pdf':
            data_bytes, mimetype = render_xrd_plot(config, output_format='pdf')
            ext = 'pdf'
        elif export_format == 'png_600':
            data_bytes, mimetype = render_xrd_plot(config, output_format='png', dpi=600)
            ext = 'png'
        else: # png_300
            data_bytes, mimetype = render_xrd_plot(config, output_format='png', dpi=300)
            ext = 'png'
            
        filename = f"XRD_Stack_Plot.{ext}"
        return send_file(
            io.BytesIO(data_bytes),
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/sample_files/<path:filename>')
def download_sample_file(filename):
    """允许从浏览器下载生成的示例数据文件"""
    return send_from_directory(SAMPLE_DIR, filename, as_attachment=True)

@app.route('/api/sample_list')
def list_sample_files():
    """获取示例文件列表"""
    if os.path.exists(SAMPLE_DIR):
        files = os.listdir(SAMPLE_DIR)
        return jsonify({"files": files})
    return jsonify({"files": []})

if __name__ == '__main__':
    print("=" * 60)
    print("XRD-Plotter 正在本地启动...")
    print("访问地址: http://127.0.0.1:5000")
    print("=" * 60)
    app.run(host='127.0.0.1', port=5000, debug=False)
