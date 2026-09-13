import io
import os
import re
import base64
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from scipy.signal import savgol_filter

# Set academic fonts with automatic CJK fallback
matplotlib.rcParams['font.sans-serif'] = ['Times New Roman', 'Arial', 'Microsoft YaHei', 'SimHei', 'DejaVu Sans']
matplotlib.rcParams['font.serif'] = ['Times New Roman', 'Microsoft YaHei', 'SimSun']
matplotlib.rcParams['axes.unicode_minus'] = False
matplotlib.rcParams['mathtext.fontset'] = 'stix'  # Times-like math font

MARKER_DICT = {
    'diamond': 'D',
    'circle': 'o',
    'square': 's',
    'triangle_up': '^',
    'triangle_down': 'v',
    'star': '*',
    'cross': 'x',
    'plus': '+',
    'none': 'None'
}

def parse_xrd_text(text_content):
    """解析 XRD 实测文本数据 (支持多种编码与分隔符)"""
    lines = text_content.strip().splitlines()
    x_vals = []
    y_vals = []
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith(('#', '@', '//', ';', '*', '!', '%')):
            continue
        # 匹配两个连续数字
        tokens = re.split(r'[\s,;\t]+', line)
        if len(tokens) >= 2:
            try:
                x = float(tokens[0])
                y = float(tokens[1])
                x_vals.append(x)
                y_vals.append(y)
            except ValueError:
                continue
                
    if not x_vals:
        raise ValueError("未能解析到有效的两列数值数据(2Theta, Intensity)")
        
    # 确保按 x 排序
    arr = sorted(zip(x_vals, y_vals), key=lambda item: item[0])
    x_sorted = [p[0] for p in arr]
    y_sorted = [p[1] for p in arr]
    return x_sorted, y_sorted

def parse_pdf_card_text(text_content):
    """解析标准 PDF 卡片数据 (2Theta, I% / Height)"""
    lines = text_content.strip().splitlines()
    peaks = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith(('#', '@', '//', ';', '*', '!', '%')):
            continue
        tokens = re.split(r'[\s,;\t]+', line)
        if len(tokens) >= 2:
            try:
                # 尝试找到两列浮点数
                angle = float(tokens[0])
                intensity = float(tokens[1])
                peaks.append({'angle': angle, 'intensity': intensity})
            except ValueError:
                continue
    if not peaks:
        raise ValueError("未能解析到标准卡片峰位数据(2Theta, I%)")
    # 归一化强度到最大 100
    max_int = max(p['intensity'] for p in peaks)
    if max_int > 0:
        for p in peaks:
            p['intensity'] = (p['intensity'] / max_int) * 100.0
    return peaks

def render_xrd_plot(config, output_format='png', dpi=300):
    """
    核心绘图引擎：依据配置生成高品质学术 XRD 谱图
    """
    settings = config.get('settings', {})
    samples = config.get('samples', [])
    pdf_cards = config.get('pdf_cards', [])
    annotations = config.get('annotations', [])
    phase_legends = config.get('phase_legends', [])
    
    # 基础样式设定
    fig_width = float(settings.get('fig_width', 8.0))
    fig_height = float(settings.get('fig_height', 5.5))
    font_family = settings.get('font_family', 'Times New Roman')
    base_font_size = float(settings.get('font_size', 12))
    line_width = float(settings.get('line_width', 1.2))
    tick_dir = settings.get('tick_direction', 'in')
    smooth_window = int(settings.get('smooth_window', 0))
    
    fig, ax = plt.subplots(figsize=(fig_width, fig_height), dpi=dpi)
    
    # 字体配置
    font_prop = {'family': font_family, 'size': base_font_size}
    
    # 坐标范围与筛选
    x_min = float(settings.get('x_min', 10.0))
    x_max = float(settings.get('x_max', 80.0))
    x_step = float(settings.get('x_step', 10.0))
    
    # 归一化与堆叠参数
    stack_gap = float(settings.get('stack_gap', 0.35))
    curve_scale = float(settings.get('curve_scale', 0.8)) # 峰高相对比例
    card_scale = float(settings.get('card_scale', 0.25))
    card_lw = float(settings.get('card_lw', 1.8))
    
    # 1. 绘制底部 PDF 标准卡片棒图 (Stick Pattern)
    card_label_x = float(settings.get('card_label_x', x_max - 2))
    card_label_y_cfg = settings.get('card_label_y')
    
    for c_idx, card in enumerate(pdf_cards):
        c_color = card.get('color', '#cc0000')
        c_name = card.get('name', f'PDF#{c_idx+1}')
        peaks = card.get('peaks', [])
        
        angles = [p['angle'] for p in peaks if x_min <= p['angle'] <= x_max]
        heights = [(p['intensity'] / 100.0) * card_scale for p in peaks if x_min <= p['angle'] <= x_max]
        
        if angles:
            ax.vlines(angles, ymin=0, ymax=heights, colors=c_color, linewidth=card_lw, zorder=2)
            
        # 卡片标签纵坐标支持自定义设定
        if card.get('label_y') is not None:
            label_y = float(card.get('label_y'))
        elif card_label_y_cfg is not None:
            label_y = float(card_label_y_cfg) + c_idx * (card_scale * 0.4)
        else:
            label_y = card_scale * (0.8 + c_idx * 0.35)

        ax.text(card_label_x, label_y, c_name, color=c_color,
                ha='right', va='bottom', fontfamily=font_family,
                fontweight='bold', fontsize=base_font_size * 0.95, zorder=5)
                
    # 2. 绘制各样品曲线
    current_baseline = card_scale + 0.08
    curves_map = {}
    top_curve_x = None
    top_curve_y = None
    
    # 归一化模式处理: independent(独立), global(全局统一放缩，保留强弱差异), raw(原始计数)
    norm_mode = settings.get('norm_mode', 'independent')
    global_max_span = 1.0
    if norm_mode == 'global':
        spans = []
        for s in samples:
            sx = np.array(s['x'])
            sy = np.array(s['y'])
            smask = (sx >= x_min) & (sx <= x_max)
            if np.any(smask):
                spans.append(np.max(sy[smask]) - np.min(sy[smask]))
        if spans and max(spans) > 0:
            global_max_span = max(spans)
            
    for s_idx, sample in enumerate(samples):
        x = np.array(sample['x'])
        y = np.array(sample['y'])
        
        # 裁剪到显示范围
        mask = (x >= x_min) & (x <= x_max)
        if not np.any(mask):
            continue
        x_sub = x[mask]
        y_sub = y[mask]
        
        # 可选平滑降噪 (Savitzky-Golay 滤波，保持晶体特征峰锐度与物理峰位)
        if smooth_window and int(smooth_window) >= 2:
            w = int(smooth_window)
            if w % 2 == 0:
                w += 1  # 强制转为奇数窗口 (scipy savgol_filter 强制要求)，解决偶数输入被彻底忽略的问题
            if len(y_sub) > w:
                try:
                    polyorder = 2 if w >= 5 else 1
                    y_sub = savgol_filter(y_sub, window_length=w, polyorder=polyorder)
                except Exception as err:
                    print(f"Savitzky-Golay smoothing error: {err}")
                
        # 依据模式归一化
        y_min_val, y_max_val = np.min(y_sub), np.max(y_sub)
        if norm_mode == 'global':
            y_norm = (y_sub - y_min_val) / global_max_span
        elif norm_mode == 'raw':
            y_norm = (y_sub - y_min_val) / 1000.0 # 保持合理尺度
        else: # independent 各自归一化
            if y_max_val > y_min_val:
                y_norm = (y_sub - y_min_val) / (y_max_val - y_min_val)
            else:
                y_norm = np.zeros_like(y_sub)
            
        # 允许单个样品独立微调 offset_y
        s_offset = float(sample.get('offset_y', 0.0))
        this_baseline = current_baseline + s_offset
        y_plot = y_norm * curve_scale + this_baseline
        
        s_color = sample.get('color', '#1f77b4')
        s_lw = float(sample.get('line_width') or line_width)
        
        ax.plot(x_sub, y_plot, color=s_color, linewidth=s_lw, zorder=3)
        
        # 样品名称标签 (如 "540℃-0.5g Se" 或 "A")，支持横纵坐标自由微调，防止与特征峰重叠
        s_name = sample.get('name', f'Sample {s_idx+1}')
        label_pos = sample.get('label_pos', 'right')
        
        if label_pos != 'none':
            # 横向 X 坐标
            if sample.get('label_x') is not None:
                lx = float(sample.get('label_x'))
                ha = 'center'
            elif settings.get('sample_label_x') is not None:
                lx = float(settings.get('sample_label_x'))
                ha = 'right' if lx > (x_min + x_max) / 2 else 'left'
            elif label_pos == 'left':
                lx = x_min + (x_max - x_min) * 0.03
                ha = 'left'
            else: # right
                lx = x_max - (x_max - x_min) * 0.06
                ha = 'right'
                
            # 纵向 Y 坐标 (相对当前基线的高度比例)
            if sample.get('label_y') is not None:
                ly = this_baseline + float(sample.get('label_y')) * curve_scale
            elif settings.get('sample_label_y') is not None:
                ly = this_baseline + float(settings.get('sample_label_y')) * curve_scale
            else:
                ly = this_baseline + 0.22 * curve_scale
                
            ax.text(lx, ly, s_name, color='#000000', fontfamily=font_family,
                    fontweight='bold', fontsize=base_font_size * 0.95, ha=ha, va='bottom', zorder=5)
                    
        # 记录各层曲线数据，便于标注指定吸附
        curves_map[sample.get('id', f'sample_{s_idx}')] = (x_sub, y_plot)
        curves_map[f'idx_{s_idx}'] = (x_sub, y_plot)
        if sample.get('name'):
            curves_map[sample.get('name')] = (x_sub, y_plot)

        if s_idx == len(samples) - 1:
            top_curve_x = x_sub
            top_curve_y = y_plot
            curves_map['top'] = (x_sub, y_plot)
            
        current_baseline += curve_scale + stack_gap
        
    # 3. 绘制晶面指数与特征峰标注 (Peak Annotations)
    if curves_map and annotations:
        marker_gap = float(settings.get('ann_marker_gap', 0.08)) # 适中悬浮间距，既不遮挡尖峰也不过远
        text_gap = float(settings.get('ann_text_gap', 0.08))
        snap_window = float(settings.get('snap_window', 1.2)) # 搜索窗口 ±1.2°，防止输入整数角度时漏脱物理峰尖
        
        for ann in annotations:
            angle = float(ann.get('angle', 0))
            if not (x_min <= angle <= x_max):
                continue
                
            text = ann.get('text', '')
            marker_name = ann.get('marker', 'none')
            color = ann.get('color', '#c0392b')
            is_vertical = ann.get('vertical', True)
            
            # 支持指定吸附到特定样品曲线 (默认最顶层 'top')
            target_key = ann.get('target', 'top')
            curve_data = curves_map.get(target_key)
            if not curve_data or curve_data[0] is None:
                curve_data = curves_map.get('top', (top_curve_x, top_curve_y))
            cur_x, cur_y = curve_data
            if cur_x is None or len(cur_x) == 0:
                continue

            # 智能峰顶吸附算法 (Local Apex Snapping):
            # 自动在角度附近 ±0.5° 搜索目标样品曲线的真实物理峰顶极大值
            if snap_window > 0:
                win_mask = (cur_x >= angle - snap_window) & (cur_x <= angle + snap_window)
                if np.any(win_mask):
                    win_indices = np.where(win_mask)[0]
                    apex_rel_idx = np.argmax(cur_y[win_mask])
                    apex_idx = win_indices[apex_rel_idx]
                    plot_x = float(cur_x[apex_idx])
                    peak_y = float(cur_y[apex_idx])
                else:
                    closest_idx = np.argmin(np.abs(cur_x - angle))
                    plot_x = angle
                    peak_y = float(cur_y[closest_idx])
            else:
                closest_idx = np.argmin(np.abs(cur_x - angle))
                plot_x = angle
                peak_y = float(cur_y[closest_idx])
            
            # 绘制几何散点符号 (若有)
            has_marker = (marker_name in MARKER_DICT and MARKER_DICT[marker_name] != 'None')
            if has_marker:
                marker_char = MARKER_DICT[marker_name]
                ax.plot(plot_x, peak_y + marker_gap, marker=marker_char,
                        color=color, markersize=7, zorder=6)
                text_y = peak_y + marker_gap + text_gap
            else:
                text_y = peak_y + marker_gap
                
            # 绘制晶面文字 (如 (112))
            if text:
                rotation = 90 if is_vertical else 0
                ax.text(plot_x, text_y, text, color=color,
                        rotation=rotation, ha='center', va='bottom',
                        fontfamily=font_family, fontweight='bold',
                        fontsize=base_font_size * 0.85, zorder=6)
                        
    # 4. 绘制右上角晶型图例 (Phase Legend)
    if settings.get('show_legend', True) and phase_legends:
        legend_handles = []
        legend_labels = []
        for pl in phase_legends:
            m_name = pl.get('marker', 'diamond')
            m_char = MARKER_DICT.get(m_name, 'D')
            m_color = pl.get('color', '#000000')
            h = Line2D([], [], marker=m_char, color=m_color,
                       markerfacecolor=m_color, markeredgecolor=m_color,
                       linestyle='None', markersize=7)
            legend_handles.append(h)
            legend_labels.append(pl.get('name', ''))
            
        leg_loc = settings.get('legend_loc', 'upper right')
        leg_ncol = int(settings.get('legend_ncol', 2))
        ax.legend(legend_handles, legend_labels, loc=leg_loc, ncol=leg_ncol,
                  frameon=False, prop={'family': font_family, 'size': base_font_size * 0.95},
                  handletextpad=0.2, columnspacing=0.8)
                  
    # 5. 坐标轴与整体装饰 (Origin 学术风格)
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(0, current_baseline + 0.3)
    
    # 刻度设置
    x_ticks = np.arange(x_min, x_max + 0.001, x_step)
    ax.set_xticks(x_ticks)
    ax.tick_params(axis='x', direction=tick_dir, which='major', length=6, width=1.2,
                   labelsize=base_font_size, top=True)
    ax.tick_params(axis='y', left=False, right=False, labelleft=False) # XRD 纵轴通常不留数字
    
    # 开启次刻度 (Minor ticks)
    ax.minorticks_on()
    ax.tick_params(axis='x', direction=tick_dir, which='minor', length=3.5, width=0.8, top=True)
    ax.tick_params(axis='y', which='minor', left=False, right=False)
    
    # 四周边框粗细 (Spines)
    spine_lw = float(settings.get('spine_width', 1.5))
    for spine in ax.spines.values():
        spine.set_linewidth(spine_lw)
        spine.set_color('#000000')
        
    # 标签
    x_label = settings.get('x_label', '2θ (degree)')
    y_label = settings.get('y_label', 'Intensity (a.u.)')
    ax.set_xlabel(x_label, fontdict={'family': font_family, 'size': base_font_size * 1.15, 'weight': 'bold'}, labelpad=8)
    ax.set_ylabel(y_label, fontdict={'family': font_family, 'size': base_font_size * 1.15, 'weight': 'bold'}, labelpad=10)
    
    # 调整布局
    plt.tight_layout()
    
    # 输出格式
    buf = io.BytesIO()
    if output_format == 'svg':
        fig.savefig(buf, format='svg')
        mimetype = 'image/svg+xml'
    elif output_format == 'pdf':
        fig.savefig(buf, format='pdf')
        mimetype = 'application/pdf'
    else:
        fig.savefig(buf, format='png', dpi=dpi)
        mimetype = 'image/png'
        
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue(), mimetype
