# -*- coding: utf-8 -*-
"""앱 아이콘(wj_app.ico) 만들기 — 웃는 얼굴 수첩. 실행: python make_icon.py  (Pillow 필요: pip install pillow)"""
import os
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
S = 1024                                                    # 크게 그린 뒤 줄여서 부드럽게


def draw():
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((40, 40, S - 40, S - 40), radius=230, fill=(255, 183, 120, 255))                 # 따뜻한 주황 바탕
    d.rounded_rectangle((40, 40, S - 40, 520), radius=230, fill=(255, 205, 150, 255))                   # 윗부분 살짝 밝게
    d.rectangle((40, 300, S - 40, 520), fill=(255, 205, 150, 255))
    d.rounded_rectangle((210, 190, 830, 860), radius=70, fill=(120, 80, 60, 70))                        # 수첩 그림자
    d.rounded_rectangle((190, 170, 810, 840), radius=70, fill=(255, 255, 255, 255))                     # 수첩 종이
    d.rounded_rectangle((190, 170, 810, 300), radius=70, fill=(255, 112, 112, 255))                     # 위쪽 빨간 띠
    d.rectangle((190, 240, 810, 300), fill=(255, 112, 112, 255))
    for x in range(285, 760, 110):                                                                      # 스프링 고리
        d.rounded_rectangle((x - 28, 110, x + 28, 250), radius=28, fill=(90, 90, 110, 255))
        d.ellipse((x - 14, 150, x + 14, 178), fill=(255, 255, 255, 255))
    for cx in (415, 585):                                                                               # 눈
        d.ellipse((cx - 38, 450, cx + 38, 540), fill=(60, 40, 40, 255))
        d.ellipse((cx - 16, 462, cx + 6, 484), fill=(255, 255, 255, 255))
    d.arc((410, 500, 590, 650), start=20, end=160, fill=(60, 40, 40, 255), width=22)                    # 웃는 입
    for cx in (345, 655):                                                                               # 볼터치
        d.ellipse((cx - 48, 545, cx + 48, 610), fill=(255, 150, 160, 190))
    for i, h in enumerate((70, 120, 90)):                                                               # 아래쪽 작은 막대그래프
        x = 380 + i * 90
        d.rounded_rectangle((x, 790 - h, x + 60, 790), radius=14, fill=(110, 200, 160, 255))
    return im


if __name__ == '__main__':
    big = draw()
    big.resize((256, 256), Image.LANCZOS).save(os.path.join(HERE, 'wj_app_preview.png'))
    sizes = [16, 24, 32, 48, 64, 128, 256]
    imgs = [big.resize((s, s), Image.LANCZOS) for s in sizes]
    imgs[-1].save(os.path.join(HERE, 'wj_app.ico'), format='ICO', sizes=[(s, s) for s in sizes], append_images=imgs[:-1])
    print('wj_app.ico 만듦')
