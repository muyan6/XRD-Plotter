// static/js/app.js - XRD-Plotter 核心前端交互与状态管理

// 全局应用状态
const state = {
  samples: [],
  pdf_cards: [],
  annotations: [],
  phase_legends: [],
  settings: {
    x_min: 10,
    x_max: 70,
    x_step: 10,
    x_label: "2θ(degree)",
    y_label: "Intensity(a.u)",
    tick_direction: "in",
    spine_width: 1.5,
    font_family: "Times New Roman",
    font_size: 12,
    line_width: 1.2,
    norm_mode: "independent",
    stack_gap: 0.38,
    curve_scale: 0.8,
    ann_marker_gap: 0.08,
    sample_label_x: 68,
    sample_label_y: 0.35,
    card_scale: 0.28,
    card_lw: 1.8,
    card_label_x: 68,
    card_label_y: 0.22,
    smooth_window: 0,
    fig_width: 8.0,
    fig_height: 5.5,
    show_legend: true,
    legend_loc: "upper right",
    legend_ncol: 2
  }
};

let renderTimer = null;
let currentImageData = null;

// 初始化
document.addEventListener('DOMContentLoaded', () => {
  initUIEvents();
  initUploads();
  initSliders();
  loadSampleFileList();
  
  // 默认载入示例2 (CZTS 系列，最完整丰富)
  loadDemo('czts');
});

// 初始化 UI 监听事件
function initUIEvents() {
  // 顶部快速分类切换标签栏
  document.querySelectorAll('.nav-tab').forEach(tabBtn => {
    tabBtn.addEventListener('click', () => {
      document.querySelectorAll('.nav-tab').forEach(b => b.classList.remove('active'));
      tabBtn.classList.add('active');

      const target = tabBtn.dataset.tab;
      const sections = document.querySelectorAll('.panel-section');

      if (target === 'all') {
        sections.forEach(s => {
          s.classList.remove('hidden-tab');
          s.classList.add('active'); // 全部展开
        });
      } else {
        sections.forEach(s => {
          if (s.dataset.section === target) {
            s.classList.remove('hidden-tab');
            s.classList.add('active'); // 选中项展开
          } else {
            s.classList.add('hidden-tab');
          }
        });
      }
      document.querySelector('.control-panel').scrollTo({ top: 0, behavior: 'smooth' });
    });
  });

  // 折叠面板展开收起
  document.querySelectorAll('.section-header').forEach(header => {
    header.addEventListener('click', () => {
      const section = header.parentElement;
      section.classList.toggle('active');
    });
  });

  // 快捷符号插入按钮
  document.querySelectorAll('.btn-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const text = chip.dataset.insert;
      const targetInput = chip.closest('.form-group').querySelector('input[type="text"]');
      if (targetInput) {
        targetInput.value = text;
        triggerAutoRender();
      }
    });
  });

  // 示例加载按钮
  document.getElementById('btn-demo-cu').addEventListener('click', () => loadDemo('cu'));
  document.getElementById('btn-demo-czts').addEventListener('click', () => loadDemo('czts'));

  // 刷新与放大
  document.getElementById('btn-refresh').addEventListener('click', () => requestRender());
  document.getElementById('btn-view-large').addEventListener('click', () => {
    if (currentImageData) {
      const win = window.open();
      win.document.write(`<img src="${currentImageData}" style="max-width:100%; height:auto;">`);
    }
  });

  // 导出菜单项点击
  document.querySelectorAll('.dropdown-content a').forEach(item => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      const format = item.dataset.format;
      exportPlot(format);
    });
  });

  // 手动录入标准卡片弹窗
  const modal = document.getElementById('manual-card-modal');
  document.getElementById('btn-manual-card').addEventListener('click', () => {
    modal.classList.add('active');
  });
  document.getElementById('btn-close-modal').addEventListener('click', () => {
    modal.classList.remove('active');
  });
  document.getElementById('btn-cancel-modal').addEventListener('click', () => {
    modal.classList.remove('active');
  });
  document.getElementById('btn-confirm-modal').addEventListener('click', handleManualCardAdd);

  // 晶面标注相关操作
  document.getElementById('btn-auto-peaks').addEventListener('click', autoDetectPeaks);
  const snapBtn = document.getElementById('btn-snap-all-angles');
  if (snapBtn) snapBtn.addEventListener('click', snapAllAngles);
  const promSlider = document.getElementById('cfg-peak-prominence');
  if (promSlider) {
    promSlider.addEventListener('input', () => {
      document.getElementById('val-peak-prominence').innerText = promSlider.value;
    });
  }
  document.getElementById('btn-add-ann').addEventListener('click', addAnnotationRow);
  document.getElementById('btn-clear-ann').addEventListener('click', clearAllAnnotations);
  document.getElementById('btn-sync-legend').addEventListener('click', syncLegendFromAnnotations);
  document.getElementById('btn-add-legend-item').addEventListener('click', addLegendItemRow);

  // 项目保存与导入
  document.getElementById('btn-save-project').addEventListener('click', saveProjectJSON);
  document.getElementById('btn-load-project-trigger').addEventListener('click', () => {
    document.getElementById('load-project-input').click();
  });
  document.getElementById('load-project-input').addEventListener('change', loadProjectJSON);

  // 基础表单输入监听
  const bindInputs = [
    { id: 'cfg-x-min', key: 'x_min', num: true },
    { id: 'cfg-x-max', key: 'x_max', num: true },
    { id: 'cfg-x-step', key: 'x_step', num: true },
    { id: 'cfg-x-label', key: 'x_label' },
    { id: 'cfg-y-label', key: 'y_label' },
    { id: 'cfg-tick-dir', key: 'tick_direction' },
    { id: 'cfg-font-family', key: 'font_family' },
    { id: 'cfg-norm-mode', key: 'norm_mode' },
    { id: 'cfg-sample-label-x', key: 'sample_label_x', num: true },
    { id: 'cfg-card-label-x', key: 'card_label_x', num: true },
    { id: 'cfg-card-label-y', key: 'card_label_y', num: true },
    { id: 'cfg-fig-w', key: 'fig_width', num: true },
    { id: 'cfg-fig-h', key: 'fig_height', num: true },
    { id: 'cfg-show-legend', key: 'show_legend', bool: true },
    { id: 'cfg-legend-ncol', key: 'legend_ncol', num: true },
    { id: 'cfg-legend-loc', key: 'legend_loc' }
  ];

  bindInputs.forEach(b => {
    const el = document.getElementById(b.id);
    if (!el) return;
    el.addEventListener('input', () => {
      let val = el.value;
      if (b.num) val = parseFloat(val) || 0;
      if (b.bool) val = (val === 'true');
      state.settings[b.key] = val;
      triggerAutoRender();
    });
    // For select elements, also listen to change
    el.addEventListener('change', () => {
      let val = el.value;
      if (b.num) val = parseFloat(val) || 0;
      if (b.bool) val = (val === 'true');
      state.settings[b.key] = val;
      triggerAutoRender();
    });
  });
}

// 初始化滑块
function initSliders() {
  const sliders = [
    { id: 'cfg-spine-width', valId: 'val-spine-width', key: 'spine_width', unit: ' pt' },
    { id: 'cfg-font-size', valId: 'val-font-size', key: 'font_size', unit: ' pt' },
    { id: 'cfg-line-width', valId: 'val-line-width', key: 'line_width', unit: ' pt' },
    { id: 'cfg-stack-gap', valId: 'val-stack-gap', key: 'stack_gap', unit: '' },
    { id: 'cfg-curve-scale', valId: 'val-curve-scale', key: 'curve_scale', unit: '' },
    { id: 'cfg-sample-label-y', valId: 'val-sample-label-y', key: 'sample_label_y', unit: '' },
    { id: 'cfg-marker-gap', valId: 'val-marker-gap', key: 'ann_marker_gap', unit: '' },
    { id: 'cfg-card-scale', valId: 'val-card-scale', key: 'card_scale', unit: '' },
    { id: 'cfg-card-lw', valId: 'val-card-lw', key: 'card_lw', unit: ' pt' },
    {
      id: 'cfg-smooth',
      valId: 'val-smooth',
      key: 'smooth_window',
      format: (v) => v == 0 ? '原始数据 (不平滑)' : `滤波窗口: ${v}`
    }
  ];

  sliders.forEach(s => {
    const slider = document.getElementById(s.id);
    const valSpan = document.getElementById(s.valId);
    if (!slider || !valSpan) return;

    slider.addEventListener('input', () => {
      const val = parseFloat(slider.value);
      state.settings[s.key] = val;
      if (s.format) {
        valSpan.innerText = s.format(val);
      } else {
        valSpan.innerText = val + s.unit;
      }
      if (s.key === 'line_width') {
        document.querySelectorAll('.sample-lw').forEach((input, sIdx) => {
          input.placeholder = val;
          if (state.samples[sIdx] && (state.samples[sIdx].line_width === null || state.samples[sIdx].line_width === undefined)) {
            input.value = val;
          }
        });
      }
      triggerAutoRender();
    });
  });
}

// 初始化文件上传
function initUploads() {
  const xrdZone = document.getElementById('xrd-upload-zone');
  const xrdInput = document.getElementById('xrd-file-input');
  
  xrdInput.addEventListener('change', (e) => {
    if (!e.target.files.length) return;
    const formData = new FormData();
    for (let f of e.target.files) {
      formData.append('files', f);
    }
    uploadXRD(formData);
    xrdInput.value = ''; // 重置，允许重复上传同一文件
  });

  // XRD 拖拽支持
  setupDropZone(xrdZone, (files) => {
    const formData = new FormData();
    for (let f of files) formData.append('files', f);
    uploadXRD(formData);
  });

  const pdfZone = document.getElementById('pdf-upload-zone');
  const pdfInput = document.getElementById('pdf-file-input');
  
  pdfInput.addEventListener('change', (e) => {
    if (!e.target.files.length) return;
    const formData = new FormData();
    for (let f of e.target.files) {
      formData.append('files', f);
    }
    uploadPDFCard(formData);
    pdfInput.value = '';
  });

  // PDF 拖拽支持
  setupDropZone(pdfZone, (files) => {
    const formData = new FormData();
    for (let f of files) formData.append('files', f);
    uploadPDFCard(formData);
  });

  // 清空样品与清空卡片按钮
  document.getElementById('btn-clear-samples').addEventListener('click', () => {
    if (confirm('确定要清空当前的全部实测样品吗？')) {
      state.samples = [];
      renderSampleList();
      triggerAutoRender(0);
    }
  });

  document.getElementById('btn-clear-cards').addEventListener('click', () => {
    if (confirm('确定要清空底部的标准卡片吗？')) {
      state.pdf_cards = [];
      renderCardList();
      triggerAutoRender(0);
    }
  });
}

// 拖拽辅助函数
function setupDropZone(zoneEl, onDropFiles) {
  if (!zoneEl) return;
  ['dragenter', 'dragover'].forEach(eventName => {
    zoneEl.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      zoneEl.style.borderColor = 'var(--primary-color)';
      zoneEl.style.backgroundColor = 'var(--primary-light)';
    });
  });

  ['dragleave', 'drop'].forEach(eventName => {
    zoneEl.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      zoneEl.style.borderColor = '#cbd5e1';
      zoneEl.style.backgroundColor = '#f8fafc';
    });
  });

  zoneEl.addEventListener('drop', (e) => {
    const dt = e.dataTransfer;
    if (dt && dt.files && dt.files.length) {
      onDropFiles(dt.files);
    }
  });
}

// 上传实测 XRD 数据
function uploadXRD(formData) {
  setRenderStatus('正在解析样品文件...', 'busy');
  fetch('/api/upload/xrd', {
    method: 'POST',
    body: formData
  })
  .then(res => res.json())
  .then(data => {
    if (data.success && data.samples) {
      // 追加样品 (新样品追加到顶部堆叠)
      state.samples = state.samples.concat(data.samples);
      renderSampleList();
      triggerAutoRender(0);
      setRenderStatus(`成功载入 ${data.samples.length} 个新样品`, 'ready');
    } else {
      alert('解析失败: ' + (data.error || '未知错误'));
    }
  })
  .catch(err => alert('网络或格式解析错误: ' + err));
}

// 上传标准卡片
function uploadPDFCard(formData) {
  setRenderStatus('正在解析卡片文件...', 'busy');
  fetch('/api/upload/pdf', {
    method: 'POST',
    body: formData
  })
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      if (data.cards) {
        state.pdf_cards = state.pdf_cards.concat(data.cards);
      } else if (data.card) {
        state.pdf_cards.push(data.card);
      }
      renderCardList();
      triggerAutoRender(0);
      setRenderStatus('标准卡片载入成功', 'ready');
    } else {
      alert('卡片解析失败: ' + (data.error || '未知错误'));
    }
  })
  .catch(err => alert('卡片解析错误: ' + err));
}

// 手动录入标准卡片处理
function handleManualCardAdd() {
  const name = document.getElementById('manual-card-name').value.trim() || 'Custom PDF';
  const color = document.getElementById('manual-card-color').value;
  const rawText = document.getElementById('manual-card-text').value.trim();

  if (!rawText) {
    alert('请输入峰位和强度数据');
    return;
  }

  const peaks = [];
  const lines = rawText.split('\n');
  for (let line of lines) {
    line = line.trim();
    if (!line) continue;
    // 支持 28.53:100, 47.33:55 这种形式
    if (line.includes(':')) {
      const parts = line.split(',');
      for (let p of parts) {
        const kv = p.split(':');
        if (kv.length >= 2) {
          peaks.push({ angle: parseFloat(kv[0]), intensity: parseFloat(kv[1]) });
        }
      }
    } else {
      const tokens = line.split(/[\s,\t]+/);
      if (tokens.length >= 2) {
        peaks.push({ angle: parseFloat(tokens[0]), intensity: parseFloat(tokens[1]) });
      }
    }
  }

  if (peaks.length === 0) {
    alert('未能解析到有效的角度和强度数据');
    return;
  }

  // 归一化强度
  const maxI = Math.max(...peaks.map(p => p.intensity));
  if (maxI > 0) {
    peaks.forEach(p => p.intensity = (p.intensity / maxI) * 100);
  }

  state.pdf_cards.push({
    id: `card_${Date.now()}`,
    name: name,
    color: color,
    peaks: peaks
  });

  document.getElementById('manual-card-modal').classList.remove('active');
  renderCardList();
  triggerAutoRender(0);
}

// 载入演示数据
function loadDemo(type) {
  setRenderStatus('载入示例数据中...', 'busy');
  fetch(`/api/demo/${type}`)
    .then(res => res.json())
    .then(data => {
      if (data.success && data.data) {
        const d = data.data;
        state.samples = d.samples || [];
        state.pdf_cards = d.pdf_cards || [];
        state.annotations = d.annotations || [];
        state.phase_legends = d.phase_legends || [];
        if (d.settings) {
          Object.assign(state.settings, d.settings);
        }
        syncSettingsToUI();
        renderSampleList();
        renderCardList();
        renderAnnotationsList();
        renderPhaseLegendList();
        triggerAutoRender(0);
      }
    });
}

// 同步状态到 UI 控件
function syncSettingsToUI() {
  const s = state.settings;
  const setVal = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.value = val;
  };
  setVal('cfg-x-min', s.x_min);
  setVal('cfg-x-max', s.x_max);
  setVal('cfg-x-step', s.x_step);
  setVal('cfg-x-label', s.x_label);
  setVal('cfg-y-label', s.y_label);
  setVal('cfg-tick-dir', s.tick_direction);
  setVal('cfg-spine-width', s.spine_width);
  setVal('cfg-font-family', s.font_family);
  setVal('cfg-font-size', s.font_size);
  setVal('cfg-line-width', s.line_width || 1.2);
  setVal('cfg-norm-mode', s.norm_mode || 'independent');
  setVal('cfg-stack-gap', s.stack_gap);
  setVal('cfg-curve-scale', s.curve_scale || 0.8);
  setVal('cfg-sample-label-x', s.sample_label_x !== undefined ? s.sample_label_x : 68);
  setVal('cfg-sample-label-y', s.sample_label_y !== undefined ? s.sample_label_y : 0.35);
  setVal('cfg-marker-gap', s.ann_marker_gap !== undefined ? s.ann_marker_gap : 0.08);
  setVal('cfg-card-scale', s.card_scale);
  setVal('cfg-card-lw', s.card_lw || 1.8);
  setVal('cfg-card-label-x', s.card_label_x);
  setVal('cfg-card-label-y', s.card_label_y !== undefined ? s.card_label_y : 0.22);
  setVal('cfg-smooth', s.smooth_window);
  setVal('cfg-fig-w', s.fig_width);
  setVal('cfg-fig-h', s.fig_height);
  setVal('cfg-show-legend', s.show_legend.toString());
  setVal('cfg-legend-ncol', s.legend_ncol);
  setVal('cfg-legend-loc', s.legend_loc);

  // 更新数值文字显示
  document.getElementById('val-spine-width').innerText = s.spine_width + ' pt';
  document.getElementById('val-font-size').innerText = s.font_size + ' pt';
  const lwEl = document.getElementById('val-line-width');
  if (lwEl) lwEl.innerText = (s.line_width || 1.2) + ' pt';
  document.getElementById('val-stack-gap').innerText = s.stack_gap;
  const csEl = document.getElementById('val-curve-scale');
  if (csEl) csEl.innerText = (s.curve_scale || 0.8).toFixed(2);
  const slyEl = document.getElementById('val-sample-label-y');
  if (slyEl) slyEl.innerText = (s.sample_label_y !== undefined ? s.sample_label_y : 0.25).toFixed(2);
  const mgEl = document.getElementById('val-marker-gap');
  if (mgEl) mgEl.innerText = (s.ann_marker_gap !== undefined ? s.ann_marker_gap : 0.08).toFixed(2);
  document.getElementById('val-card-scale').innerText = s.card_scale;
  const clwEl = document.getElementById('val-card-lw');
  if (clwEl) clwEl.innerText = (s.card_lw || 1.8) + ' pt';
  document.getElementById('val-smooth').innerText = s.smooth_window == 0 ? '原始数据 (不平滑)' : `滤波窗口: ${s.smooth_window}`;
}

// 渲染样品列表
function renderSampleList() {
  const container = document.getElementById('samples-list');
  container.innerHTML = '';
  document.getElementById('sample-count').innerText = `${state.samples.length} 样品`;

  state.samples.forEach((sample, idx) => {
    const row = document.createElement('div');
    row.className = 'list-row';
    const lwVal = (sample.line_width !== undefined && sample.line_width !== null) ? sample.line_width : (state.settings.line_width || 1.2);
    row.innerHTML = `
      <input type="color" value="${sample.color}" title="曲线颜色" data-idx="${idx}" class="sample-color">
      <input type="text" value="${sample.name}" title="样品名称" class="item-name-input sample-name" data-idx="${idx}">
      <select class="sample-pos" data-idx="${idx}" title="名称标注位置">
        <option value="right" ${sample.label_pos === 'right' ? 'selected' : ''}>靠右</option>
        <option value="left" ${sample.label_pos === 'left' ? 'selected' : ''}>靠左</option>
        <option value="none" ${sample.label_pos === 'none' ? 'selected' : ''}>隐藏</option>
      </select>
      <input type="number" step="0.1" min="0.5" max="5" value="${lwVal}" placeholder="${state.settings.line_width || 1.2}" title="曲线粗细 (pt)" class="sample-lw" style="width:52px; padding:4px 2px; font-size:0.75rem; text-align:center;">
      <button class="btn-icon btn-move-up" title="上移层级" data-idx="${idx}">▲</button>
      <button class="btn-icon btn-move-down" title="下移层级" data-idx="${idx}">▼</button>
      <button class="btn-icon btn-del-sample" title="删除" data-idx="${idx}">✕</button>
    `;

    // 事件绑定
    row.querySelector('.sample-color').addEventListener('input', (e) => {
      sample.color = e.target.value;
      triggerAutoRender();
    });
    row.querySelector('.sample-name').addEventListener('input', (e) => {
      sample.name = e.target.value;
      triggerAutoRender();
    });
    row.querySelector('.sample-name').addEventListener('change', () => {
      renderAnnotationsList();
    });
    row.querySelector('.sample-pos').addEventListener('change', (e) => {
      sample.label_pos = e.target.value;
      triggerAutoRender();
    });
    row.querySelector('.sample-lw').addEventListener('input', (e) => {
      const v = parseFloat(e.target.value);
      sample.line_width = isNaN(v) ? null : v;
      triggerAutoRender();
    });
    row.querySelector('.btn-move-up').addEventListener('click', () => {
      if (idx > 0) {
        const temp = state.samples[idx];
        state.samples[idx] = state.samples[idx - 1];
        state.samples[idx - 1] = temp;
        renderSampleList();
        triggerAutoRender();
      }
    });
    row.querySelector('.btn-move-down').addEventListener('click', () => {
      if (idx < state.samples.length - 1) {
        const temp = state.samples[idx];
        state.samples[idx] = state.samples[idx + 1];
        state.samples[idx + 1] = temp;
        renderSampleList();
        triggerAutoRender();
      }
    });
    row.querySelector('.btn-del-sample').addEventListener('click', () => {
      state.samples.splice(idx, 1);
      renderSampleList();
      triggerAutoRender();
    });

    container.appendChild(row);
  });

  // 同步更新找峰目标样品下拉菜单 (自顶向下)
  const autoPeakTargetSelect = document.getElementById('cfg-auto-peak-target');
  if (autoPeakTargetSelect) {
    const curVal = autoPeakTargetSelect.value || 'top';
    let opts = '<option value="top">[顶层] 最顶层样品 (默认)</option>';
    const total = state.samples.length;
    for (let i = total - 1; i >= 0; i--) {
      const s = state.samples[i];
      let layerTag = '中层';
      if (i === total - 1) layerTag = '顶层';
      else if (i === 0) layerTag = '底层';
      opts += `<option value="${s.id || 'idx_' + i}">[${layerTag}] ${s.name || '样品 ' + (i + 1)}</option>`;
    }
    autoPeakTargetSelect.innerHTML = opts;
    autoPeakTargetSelect.value = curVal;
  }
}

// 渲染标准卡片列表
function renderCardList() {
  const container = document.getElementById('cards-list');
  container.innerHTML = '';

  state.pdf_cards.forEach((card, idx) => {
    const row = document.createElement('div');
    row.className = 'list-row';
    row.innerHTML = `
      <input type="color" value="${card.color}" title="卡片棒线颜色" class="card-color" data-idx="${idx}">
      <input type="text" value="${card.name}" title="卡片说明" class="item-name-input card-name" data-idx="${idx}">
      <span style="font-size:0.75rem; color:#64748b;">${card.peaks ? card.peaks.length : 0}峰</span>
      <button class="btn-icon btn-del-card" title="删除卡片" data-idx="${idx}">✕</button>
    `;

    row.querySelector('.card-color').addEventListener('input', (e) => {
      card.color = e.target.value;
      triggerAutoRender();
    });
    row.querySelector('.card-name').addEventListener('input', (e) => {
      card.name = e.target.value;
      triggerAutoRender();
    });
    row.querySelector('.btn-del-card').addEventListener('click', () => {
      state.pdf_cards.splice(idx, 1);
      renderCardList();
      triggerAutoRender();
    });

    container.appendChild(row);
  });
}

// 渲染晶面标注列表 (hkl)
function renderAnnotationsList() {
  const container = document.getElementById('annotations-list');
  container.innerHTML = '';
  document.getElementById('ann-count').innerText = `${state.annotations.length} 标注`;

  const markerOptions = [
    { val: 'none', label: '无符号(纯晶面)' },
    { val: 'diamond', label: '♦ 菱形' },
    { val: 'circle', label: '● 圆点' },
    { val: 'triangle_up', label: '▲ 正三角' },
    { val: 'triangle_down', label: '▼ 倒三角' },
    { val: 'square', label: '■ 正方形' },
    { val: 'star', label: '★ 五角星' },
    { val: 'cross', label: '✕ 叉乘' },
    { val: 'plus', label: '+ 加号' }
  ];

  // 按照人类直觉自顶向下排列层级：顶层 -> 中层 -> 底层
  const sampleTargetOptions = [
    { val: 'top', label: '[顶层] 最顶层曲线' }
  ];
  const total = state.samples.length;
  for (let i = total - 1; i >= 0; i--) {
    const s = state.samples[i];
    let layerTag = '中层';
    if (i === total - 1) layerTag = '顶层';
    else if (i === 0) layerTag = '底层';
    sampleTargetOptions.push({
      val: s.id || `idx_${i}`,
      label: `[${layerTag}] ${s.name || '样品 ' + (i + 1)}`
    });
  }

  state.annotations.forEach((ann, idx) => {
    const row = document.createElement('div');
    row.className = 'ann-row';
    
    let optHtml = markerOptions.map(m => 
      `<option value="${m.val}" ${ann.marker === m.val ? 'selected' : ''}>${m.label}</option>`
    ).join('');

    let targetHtml = sampleTargetOptions.map(t =>
      `<option value="${t.val}" ${(ann.target || 'top') === t.val ? 'selected' : ''}>${t.label}</option>`
    ).join('');

    row.innerHTML = `
      <input type="number" step="0.1" value="${ann.angle}" placeholder="角度" title="2θ 角度" class="ann-angle" style="padding:3px;">
      <input type="text" value="${ann.text}" placeholder="晶面" title="晶面指数如 (112)" class="ann-text" style="padding:3px;">
      <select class="ann-marker" title="物相标记符号">${optHtml}</select>
      <select class="ann-target" title="吸附于哪条样品曲线">${targetHtml}</select>
      <input type="color" value="${ann.color || '#c0392b'}" class="ann-color" style="width:24px; height:24px; border:none; padding:0; cursor:pointer;" title="标记颜色">
      <button class="btn-icon btn-del-ann" title="删除标注">✕</button>
    `;

    row.querySelector('.ann-angle').addEventListener('input', (e) => {
      ann.angle = parseFloat(e.target.value) || 0;
      triggerAutoRender();
    });
    row.querySelector('.ann-text').addEventListener('input', (e) => {
      ann.text = e.target.value;
      triggerAutoRender();
    });
    row.querySelector('.ann-marker').addEventListener('change', (e) => {
      ann.marker = e.target.value;
      triggerAutoRender();
    });
    row.querySelector('.ann-target').addEventListener('change', (e) => {
      ann.target = e.target.value;
      triggerAutoRender();
    });
    row.querySelector('.ann-color').addEventListener('input', (e) => {
      ann.color = e.target.value;
      triggerAutoRender();
    });
    row.querySelector('.btn-del-ann').addEventListener('click', () => {
      state.annotations.splice(idx, 1);
      renderAnnotationsList();
      triggerAutoRender();
    });

    container.appendChild(row);
  });
}

// 智能自动找峰 (支持指定目标样品与灵敏度阈值)
function autoDetectPeaks() {
  if (!state.samples.length) {
    alert('请先上传或载入 XRD 实测样品数据！');
    return;
  }
  const targetId = document.getElementById('cfg-auto-peak-target') ? document.getElementById('cfg-auto-peak-target').value : 'top';
  const prominence = document.getElementById('cfg-peak-prominence') ? parseFloat(document.getElementById('cfg-peak-prominence').value) : 0.035;

  setRenderStatus('正在智能识别特征峰...', 'busy');
  fetch('/api/auto_peaks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      samples: state.samples,
      settings: state.settings,
      target_sample_id: targetId,
      prominence: prominence
    })
  })
  .then(res => res.json())
  .then(data => {
    if (data.success && data.annotations) {
      if (state.annotations.length > 0) {
        const replaceAll = confirm(
          `在【${data.sample_name}】上成功识别出 ${data.count} 个特征峰！\n\n` +
          `点击【确定】：清空并替换为本次新识别的 ${data.count} 个峰\n` +
          `点击【取消】：保留已有标注，将本次新峰追加到列表末尾`
        );
        if (replaceAll) {
          state.annotations = data.annotations;
        } else {
          state.annotations = state.annotations.concat(data.annotations);
        }
      } else {
        state.annotations = data.annotations;
      }
      renderAnnotationsList();
      triggerAutoRender(0);
      setRenderStatus(`识别成功！在【${data.sample_name}】上自左向右识别出 ${data.count} 个特征峰`, 'ready');
    } else {
      alert('自动找峰完成: ' + (data.error || '未发现明显峰'));
      setRenderStatus('找峰完成', 'ready');
    }
  })
  .catch(err => {
    alert('通信异常: ' + err);
    setRenderStatus('识别出错', 'error');
  });
}

// 一键校准所有峰位到真实物理峰尖
function snapAllAngles() {
  if (!state.annotations.length) {
    alert('当前没有需要校准的标注项');
    return;
  }
  setRenderStatus('正在精确校准所有峰顶位置...', 'busy');
  fetch('/api/snap_angles', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      samples: state.samples,
      annotations: state.annotations
    })
  })
  .then(res => res.json())
  .then(data => {
    if (data.success && data.annotations) {
      state.annotations = data.annotations;
      renderAnnotationsList();
      triggerAutoRender(0);
      setRenderStatus('所有标注已精准对齐至物理峰尖极大值！', 'ready');
    }
  })
  .catch(err => alert('校准通信异常: ' + err));
}

// 清空所有标注
function clearAllAnnotations() {
  state.annotations = [];
  renderAnnotationsList();
  triggerAutoRender(0);
}

// 手动添加单个标注 (自动循环选用下一个不同图标)
function addAnnotationRow() {
  const markerCycle = ['diamond', 'triangle_up', 'circle', 'square', 'triangle_down', 'cross', 'star', 'plus'];
  const colorCycle = ['#c0392b', '#1f77b4', '#228b22', '#2c3e50', '#8e44ad', '#d35400', '#008b8b', '#c71585'];

  const nextIdx = state.annotations.length % markerCycle.length;
  let nextAngle = 30.0;
  if (state.annotations.length > 0) {
    const last = state.annotations[state.annotations.length - 1];
    nextAngle = Math.min(state.settings.x_max - 2, Math.round((last.angle + 8.0) * 10) / 10);
  } else {
    nextAngle = Math.round((state.settings.x_min + (state.settings.x_max - state.settings.x_min) * 0.3) * 10) / 10;
  }

  state.annotations.push({
    angle: nextAngle,
    text: "",
    marker: markerCycle[nextIdx],
    color: colorCycle[nextIdx],
    vertical: true
  });
  renderAnnotationsList();
  triggerAutoRender();
}

// 从当前标注同步生成右上角图例
function syncLegendFromAnnotations() {
  if (!state.annotations.length) {
    alert('当前没有任何特征峰标注，请先添加标注或点击自动找峰！');
    return;
  }
  const seen = new Set();
  const newLegends = [];
  state.annotations.forEach(ann => {
    if (ann.marker && ann.marker !== 'none' && !seen.has(ann.marker)) {
      seen.add(ann.marker);
      newLegends.push({
        name: ann.text || `Phase_${newLegends.length + 1}`,
        marker: ann.marker,
        color: ann.color || '#000000'
      });
    }
  });

  if (newLegends.length > 0) {
    state.phase_legends = newLegends;
    state.settings.show_legend = true;
    syncSettingsToUI();
    renderPhaseLegendList();
    triggerAutoRender();
    setRenderStatus(`已成功从标注同步生成 ${newLegends.length} 个物相图例`, 'ready');
  }
}

// 渲染右上角物相图例列表
function renderPhaseLegendList() {
  const container = document.getElementById('legend-items-list');
  container.innerHTML = '';

  const markerOptions = [
    { val: 'diamond', label: '♦ 菱形' },
    { val: 'circle', label: '● 圆点' },
    { val: 'triangle_up', label: '▲ 正三角' },
    { val: 'triangle_down', label: '▼ 倒三角' },
    { val: 'square', label: '■ 正方形' },
    { val: 'star', label: '★ 五角星' },
    { val: 'cross', label: '✕ 叉乘' },
    { val: 'plus', label: '+ 加号' }
  ];

  state.phase_legends.forEach((item, idx) => {
    const row = document.createElement('div');
    row.className = 'list-row';

    let optHtml = markerOptions.map(m => 
      `<option value="${m.val}" ${item.marker === m.val ? 'selected' : ''}>${m.label}</option>`
    ).join('');

    row.innerHTML = `
      <select class="pl-marker">${optHtml}</select>
      <input type="text" value="${item.name}" placeholder="物相名称 (如 MoSe₂)" class="item-name-input pl-name">
      <input type="color" value="${item.color || '#000000'}" class="pl-color">
      <button class="btn-icon btn-del-pl" title="删除">✕</button>
    `;

    row.querySelector('.pl-marker').addEventListener('change', (e) => {
      item.marker = e.target.value;
      triggerAutoRender();
    });
    row.querySelector('.pl-name').addEventListener('input', (e) => {
      item.name = e.target.value;
      triggerAutoRender();
    });
    row.querySelector('.pl-color').addEventListener('input', (e) => {
      item.color = e.target.value;
      triggerAutoRender();
    });
    row.querySelector('.btn-del-pl').addEventListener('click', () => {
      state.phase_legends.splice(idx, 1);
      renderPhaseLegendList();
      triggerAutoRender();
    });

    container.appendChild(row);
  });
}

function addLegendItemRow() {
  state.phase_legends.push({
    name: "NewPhase",
    marker: "circle",
    color: "#000000"
  });
  renderPhaseLegendList();
  triggerAutoRender();
}

// 防抖自动触发重新渲染
function triggerAutoRender(delay = 200) {
  if (renderTimer) clearTimeout(renderTimer);
  renderTimer = setTimeout(() => {
    requestRender();
  }, delay);
}

// 请求后端渲染出图
function requestRender() {
  setRenderStatus('正在极速渲染...', 'busy');
  const overlay = document.getElementById('loading-overlay');
  overlay.style.display = 'flex';

  const payload = {
    settings: state.settings,
    samples: state.samples,
    pdf_cards: state.pdf_cards,
    annotations: state.annotations,
    phase_legends: state.phase_legends
  };

  fetch('/api/plot', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
  .then(res => res.json())
  .then(data => {
    overlay.style.display = 'none';
    if (data.success && data.image) {
      currentImageData = data.image;
      const img = document.getElementById('plot-image');
      img.src = data.image;
      setRenderStatus('渲染完成 · 实时同步', 'ready');
    } else {
      setRenderStatus('渲染出错: ' + (data.error || '错误'), 'error');
    }
  })
  .catch(err => {
    overlay.style.display = 'none';
    setRenderStatus('请求通信失败: ' + err, 'error');
  });
}

// 导出图表 (300/600 DPI, SVG, PDF)
function exportPlot(format) {
  setRenderStatus('正在生成高分辨率导出文件...', 'busy');
  const payload = {
    export_format: format,
    settings: state.settings,
    samples: state.samples,
    pdf_cards: state.pdf_cards,
    annotations: state.annotations,
    phase_legends: state.phase_legends
  };

  fetch('/api/export', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
  .then(res => {
    if (!res.ok) throw new Error('导出处理失败');
    return res.blob();
  })
  .then(blob => {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    let ext = 'png';
    if (format === 'svg') ext = 'svg';
    else if (format === 'pdf') ext = 'pdf';
    a.download = `XRD_Stack_Plot_${format}.${ext}`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
    setRenderStatus('导出文件下载成功', 'ready');
  })
  .catch(err => {
    setRenderStatus('导出失败: ' + err, 'error');
  });
}

// 保存工程 JSON
function saveProjectJSON() {
  const jsonStr = JSON.stringify(state, null, 2);
  const blob = new Blob([jsonStr], { type: 'application/json' });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `XRD_Project_${new Date().toISOString().slice(0,10)}.json`;
  a.click();
  window.URL.revokeObjectURL(url);
}

// 载入工程 JSON
function loadProjectJSON(e) {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (event) => {
    try {
      const loaded = JSON.parse(event.target.result);
      if (loaded.samples) state.samples = loaded.samples;
      if (loaded.pdf_cards) state.pdf_cards = loaded.pdf_cards;
      if (loaded.annotations) state.annotations = loaded.annotations;
      if (loaded.phase_legends) state.phase_legends = loaded.phase_legends;
      if (loaded.settings) Object.assign(state.settings, loaded.settings);

      syncSettingsToUI();
      renderSampleList();
      renderCardList();
      renderAnnotationsList();
      renderPhaseLegendList();
      triggerAutoRender(0);
      alert('工程配置加载成功！');
    } catch (err) {
      alert('配置文件格式错误: ' + err);
    }
  };
  reader.readAsText(file);
}

// 状态文字指示
function setRenderStatus(text, type = 'ready') {
  const el = document.getElementById('render-status');
  const dot = document.querySelector('.status-dot');
  if (el) el.innerText = text;
  if (dot) {
    if (type === 'busy') dot.style.backgroundColor = '#f59e0b';
    else if (type === 'error') dot.style.backgroundColor = '#ef4444';
    else dot.style.backgroundColor = '#22c55e';
  }
}

// 加载示例文件下载链接
function loadSampleFileList() {
  fetch('/api/sample_list')
    .then(res => res.json())
    .then(data => {
      const container = document.getElementById('sample-download-links');
      if (data.files && data.files.length) {
        container.innerHTML = data.files.map(f => 
          `<a href="/sample_files/${encodeURIComponent(f)}" download title="点击下载此示例文件">${f}</a>`
        ).join('');
      }
    })
    .catch(() => {});
}
