from flask import Flask, render_template
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re

app = Flask(__name__)

def get_movie_data(query_type):
    movie_list = []
    blacklist = ['이런 영화 어때요', '상영예정작', '박스오피스', '순위', '전체보기', '도움말', '더보기', '영화', '관람객', '내 평점']
    
    try:
        session = requests.Session()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Referer': 'https://www.naver.com/'
        }
        url = f"https://search.naver.com/search.naver?query={query_type}"
        res = session.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # ✅ 1. 개봉 예정작 로직 (D-n 영화 제목 형식)
        if "예정" in query_type or "상영예정" in query_type:
            # 더 넓은 범위의 아이템 선택자 사용
            items = soup.select('.item_list li, ._item, .cm_content_area li, .data_area, .movie_info')
            seen_titles = set()
            
            for item in items:
                title_el = item.select_one('.name, .title, ._text, .strong, b')
                # D-Day가 들어있을 법한 모든 곳을 탐색
                info_els = item.select('.dday, .info_txt, .txt, .sub_text, .desc, .info')
                
                if title_el:
                    title = title_el.get_text().strip()
                    # 제목 정제 및 중복/블랙리스트 체크
                    if not title or title in seen_titles or any(w in title for w in blacklist) or len(title) <= 1:
                        continue
                    
                    d_day_found = ""
                    for info in info_els:
                        info_text = info.get_text().strip()
                        # "D-숫자" 형태만 정규식으로 추출
                        match = re.search(r'D-\d+', info_text)
                        if match:
                            d_day_found = match.group()
                            break
                    
                    # 형식 맞춰서 추가
                    if d_day_found:
                        movie_list.append(f"{d_day_found} {title}")
                    else:
                        # D-Day가 없으면 제목만이라도 추가
                        movie_list.append(title)
                        
                    seen_titles.add(title)
                if len(movie_list) >= 10: break
            return movie_list

        # ✅ 2. 평점 정보 (기존 정상 작동 로직)
        elif "평점" in query_type or query_type == "영화":
            items = soup.select('.item_list li, ._item, .movie_info, .data_area')
            for item in items:
                name_el = item.select_one('.name, .title, ._text, .strong')
                score_el = item.select_one('.num, .score, .rating, ._score')
                if name_el and score_el:
                    name, score = name_el.get_text().strip(), score_el.get_text().strip()
                    if name and score and any(c.isdigit() for c in score):
                        if name not in [m['m_title'] for m in movie_list] and not any(w in name for w in blacklist):
                            movie_list.append({'m_title': name, 'm_rating': score})
                if len(movie_list) >= 10: break
            return movie_list

        # ✅ 3. 홈 화면 (박스오피스)
        else:
            items = soup.select('.name, .title, ._text')
            for item in items:
                txt = item.get_text().strip()
                if txt and not any(w in txt for w in blacklist) and txt not in movie_list:
                    movie_list.append(txt)
                if len(movie_list) >= 10: break
            return movie_list

    except Exception as e:
        print(f"에러 발생: {e}")
    return movie_list

@app.route('/')
def home():
    box_office = get_movie_data("박스오피스+순위")
    current_date = datetime.now().strftime("%Y년 %m월 %d일")
    return render_template('index.html', box_office=box_office, date=current_date)

@app.route('/upcoming')
def upcoming_page():
    # 검색어를 네이버가 가장 잘 인식하는 형태로 고정
    upcoming = get_movie_data("상영예정영화")
    current_date = datetime.now().strftime("%Y년 %m월 %d일")
    return render_template('upcoming.html', upcoming=upcoming, date=current_date)

@app.route('/ratings')
def ratings_page():
    movie_ratings = get_movie_data("영화")
    current_date = datetime.now().strftime("%Y년 %m월 %d일")
    return render_template('review.html', movies=movie_ratings, date=current_date)

if __name__ == '__main__':
    app.run(debug=True)