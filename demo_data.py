"""
demo_data.py - 生成逼真的 XRD 演示数据与标准 PDF 卡片数据
用于一键载入测试及作为用户输入文件的格式参考
"""
import numpy as np

def gaussian(x, x0, fwhm, height):
    sigma = fwhm / (2 * np.sqrt(2 * np.log(2)))
    return height * np.exp(-((x - x0) ** 2) / (2 * sigma ** 2))

def pseudo_voigt(x, x0, fwhm, height, eta=0.5):
    # eta=1: Lorentzian, eta=0: Gaussian
    sigma = fwhm / (2 * np.sqrt(2 * np.log(2)))
    gamma = fwhm / 2.0
    g = np.exp(-((x - x0) ** 2) / (2 * sigma ** 2))
    l = (gamma ** 2) / ((x - x0) ** 2 + gamma ** 2)
    return height * (eta * l + (1 - eta) * g)

def generate_demo_cu_series():
    """生成 Cu / Cu2O 系列（对应截图1）"""
    two_theta = np.linspace(20, 80, 1201)  # step = 0.05
    
    # Cu standard card peaks (2theta, rel_intensity)
    cu_card = [
        {"angle": 43.297, "intensity": 100.0, "hkl": "111"},
        {"angle": 50.433, "intensity": 46.0, "hkl": "200"},
        {"angle": 74.130, "intensity": 20.0, "hkl": "220"}
    ]
    
    # Cu2O standard card peaks
    cu2o_card = [
        {"angle": 29.554, "intensity": 9.0, "hkl": "110"},
        {"angle": 36.418, "intensity": 100.0, "hkl": "111"},
        {"angle": 42.296, "intensity": 37.0, "hkl": "200"},
        {"angle": 61.343, "intensity": 27.0, "hkl": "220"},
        {"angle": 73.526, "intensity": 8.0, "hkl": "311"},
        {"angle": 77.545, "intensity": 7.0, "hkl": "222"}
    ]
    
    np.random.seed(42)
    bg = 50 + 20 * np.sin(two_theta / 30)
    
    # Sample A: Pure Cu with high crystallinity
    y_A = bg + np.random.normal(0, 3, len(two_theta))
    for p in cu_card:
        y_A += pseudo_voigt(two_theta, p["angle"], 0.28, p["intensity"] * 9.5)
        
    # Sample B: Cu with slight peak broadening
    y_B = bg + np.random.normal(0, 3.5, len(two_theta))
    for p in cu_card:
        y_B += pseudo_voigt(two_theta, p["angle"], 0.32, p["intensity"] * 8.8)
        
    # Sample C: Cu2O
    y_C = bg + np.random.normal(0, 4, len(two_theta))
    for p in cu2o_card:
        y_C += pseudo_voigt(two_theta, p["angle"], 0.35, p["intensity"] * 8.0)
        
    return {
        "x": two_theta.tolist(),
        "samples": [
            {"id": "sample_C", "name": "C", "color": "#b8860b", "label_pos": "left", "y": np.round(y_C, 2).tolist()},
            {"id": "sample_B", "name": "B", "color": "#008b8b", "label_pos": "left", "y": np.round(y_B, 2).tolist()},
            {"id": "sample_A", "name": "A", "color": "#1f77b4", "label_pos": "left", "y": np.round(y_A, 2).tolist()}
        ],
        "pdf_cards": [
            {
                "id": "card_cu",
                "name": "Cu PDF#04-0836",
                "color": "#cc0000",
                "peaks": [{"angle": p["angle"], "intensity": p["intensity"]} for p in cu_card]
            },
            {
                "id": "card_cu2o",
                "name": "Cu2O PDF#99-0041",
                "color": "#1e90ff",
                "peaks": [{"angle": p["angle"], "intensity": p["intensity"]} for p in cu2o_card]
            }
        ],
        "settings": {
            "x_min": 20,
            "x_max": 80,
            "x_step": 20,
            "x_label": "2θ / °",
            "y_label": "Intensity / a.u.",
            "stack_gap": 0.45,
            "card_scale": 0.3,
            "card_label_x": 78,
            "card_label_y": 0.24,
            "show_legend": False
        }
    }

def generate_demo_czts_series():
    """生成 CZTS / MoSe2 / Mo 系列（对应截图2，含晶面及学术标记）"""
    two_theta = np.linspace(10, 70, 1201)
    
    # CZTS standard card PDF#26-0575
    czts_card = [
        {"angle": 16.32, "intensity": 5.0, "hkl": "101"},
        {"angle": 18.25, "intensity": 8.0, "hkl": "110"},
        {"angle": 23.12, "intensity": 6.0, "hkl": "103"},
        {"angle": 28.53, "intensity": 100.0, "hkl": "112"},
        {"angle": 29.80, "intensity": 10.0, "hkl": "105"},
        {"angle": 32.99, "intensity": 12.0, "hkl": "200"},
        {"angle": 37.08, "intensity": 10.0, "hkl": "211"},
        {"angle": 38.05, "intensity": 8.0, "hkl": "107"},
        {"angle": 45.10, "intensity": 12.0, "hkl": "204"},
        {"angle": 47.33, "intensity": 55.0, "hkl": "220"},
        {"angle": 54.20, "intensity": 6.0, "hkl": "310"},
        {"angle": 56.18, "intensity": 25.0, "hkl": "312"},
        {"angle": 58.97, "intensity": 18.0, "hkl": "224"},
        {"angle": 64.20, "intensity": 8.0, "hkl": "316"},
        {"angle": 69.23, "intensity": 14.0, "hkl": "400"}
    ]
    
    np.random.seed(101)
    bg = 40 + 10 * np.exp(-two_theta / 20)
    
    # Sample 1: 540℃-0.5g Se
    y_1 = bg + np.random.normal(0, 2.5, len(two_theta))
    for p in czts_card:
        y_1 += pseudo_voigt(two_theta, p["angle"], 0.28, p["intensity"] * 9.0)
    # add Mo peak at 40.5
    y_1 += pseudo_voigt(two_theta, 40.5, 0.30, 450)
    # add MoSe2 peaks at 31.8, 55.8
    y_1 += pseudo_voigt(two_theta, 31.8, 0.60, 60)
    y_1 += pseudo_voigt(two_theta, 55.8, 0.55, 70)
    # Cu2S peak at 29.3
    y_1 += pseudo_voigt(two_theta, 29.3, 0.25, 50)
    
    # Sample 2: 550℃-0.7g Se (上)
    y_2 = bg + np.random.normal(0, 2.8, len(two_theta))
    for p in czts_card:
        y_2 += pseudo_voigt(two_theta, p["angle"], 0.32, p["intensity"] * 7.5)
    y_2 += pseudo_voigt(two_theta, 40.5, 0.32, 280)
    y_2 += pseudo_voigt(two_theta, 31.8, 0.65, 45)
    
    # Sample 3: 550℃-0.7g Se (下)
    y_3 = bg + np.random.normal(0, 3.0, len(two_theta))
    for p in czts_card:
        y_3 += pseudo_voigt(two_theta, p["angle"], 0.35, p["intensity"] * 6.5)
    y_3 += pseudo_voigt(two_theta, 40.5, 0.35, 250)
    y_3 += pseudo_voigt(two_theta, 53.6, 0.40, 110)
    
    return {
        "x": two_theta.tolist(),
        "samples": [
            {"id": "s3", "name": "550℃-0.7g Se (II)", "color": "#2c3e50", "y": np.round(y_3, 2).tolist()},
            {"id": "s2", "name": "550℃-0.7g Se (I)", "color": "#c0392b", "y": np.round(y_2, 2).tolist()},
            {"id": "s1", "name": "540℃-0.5g Se", "color": "#1f77b4", "y": np.round(y_1, 2).tolist()}
        ],
        "pdf_cards": [
            {
                "id": "card_czts",
                "name": "CZTS PDF#26-0575",
                "color": "#800080",
                "peaks": [{"angle": p["angle"], "intensity": p["intensity"]} for p in czts_card]
            }
        ],
        "annotations": [
            {"angle": 18.25, "text": "(101)", "marker": "diamond", "color": "#c0392b", "vertical": True},
            {"angle": 23.12, "text": "(110)", "marker": "diamond", "color": "#c0392b", "vertical": True},
            {"angle": 25.1, "text": "", "marker": "cross", "color": "#000000", "vertical": True},
            {"angle": 28.53, "text": "(112)", "marker": "diamond", "color": "#c0392b", "vertical": True},
            {"angle": 29.3, "text": "", "marker": "triangle_down", "color": "#c71585", "vertical": True},
            {"angle": 31.8, "text": "", "marker": "triangle_up", "color": "#228b22", "vertical": True},
            {"angle": 37.08, "text": "(211)", "marker": "diamond", "color": "#c0392b", "vertical": True},
            {"angle": 40.5, "text": "", "marker": "circle", "color": "#000000", "vertical": True},
            {"angle": 47.33, "text": "(204)", "marker": "diamond", "color": "#c0392b", "vertical": True},
            {"angle": 56.18, "text": "(312)", "marker": "diamond", "color": "#c0392b", "vertical": True},
            {"angle": 57.0, "text": "", "marker": "triangle_up", "color": "#228b22", "vertical": True},
            {"angle": 69.23, "text": "(400)", "marker": "diamond", "color": "#c0392b", "vertical": True}
        ],
        "phase_legends": [
            {"name": "MoSe₂", "marker": "triangle_up", "color": "#228b22"},
            {"name": "CZTSSe", "marker": "diamond", "color": "#c0392b"},
            {"name": "Mo", "marker": "circle", "color": "#000000"},
            {"name": "Cu₂Se_x", "marker": "cross", "color": "#000000"},
            {"name": "Cu₂S", "marker": "triangle_down", "color": "#c71585"}
        ],
        "settings": {
            "x_min": 10,
            "x_max": 70,
            "x_step": 10,
            "x_label": "2θ(degree)",
            "y_label": "Intensity(a.u)",
            "stack_gap": 0.38,
            "ann_marker_gap": 0.08,
            "sample_label_x": 68,
            "sample_label_y": 0.35,
            "card_scale": 0.28,
            "card_label_x": 68,
            "card_label_y": 0.22,
            "show_legend": True
        }
    }
