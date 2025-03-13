import streamlit as st
from st_keyup import st_keyup
import mysql.connector  # Ensure this import is present
from mysql.connector import Error
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(layout="wide")
# MySQL 数据库配置
db_config = {
    'host': '111.119.242.63',
    'port': 3306,
    'user': 'zhukeyun',
    'password': 'yytt0324',
    'database': 'media_corpus'
}

# 主题分组映射
THEME_GROUPS = {
    '股市': ['A股盘面直播', '港股动态', '美股动态', 'A股公告速递', '期货市场情报', '股指期货', '券商动态', '禽畜期货', '能源类期货', '黄金'],
    '经济': ['环球市场情报', '银行业动态', '经济数据及解读'],
    '科技': ['人工智能', '数字经济', '云计算', 'AI智能体', '算力租赁', '国资云', '半导体芯片', 'HBM', '固态电池', '算力', '算力芯片', '机器人', '智能驾驶', '智能制造', '汽车大新闻', '华为最新动态', '5G'],
    '军事': ['俄乌冲突快报', '海工装备'],
    '社会': ['地震快讯', '医药', '旅游酒店', '纪委动态'],
    '农业': ['猪肉', '家禽', '水产', '白酒'],
    '工业': ['有色·铜', '原油市场动态', '石油化工', '民航机场', '有色金属', '柴油发电机'],
    '其他': ['TMT行业观察']
}

# 连接数据库
def connect_db():
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except Error as e:
        st.error(f"数据库连接失败: {e}")
        return None

# 查询新闻和主题数据
@st.cache_data
def fetch_news_with_subjects(start_time=None, end_time=None):
    conn = connect_db()
    if conn is None:
        return []
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
            SELECT n.id, n.ctime, n.content, n.reading_num, n.comment_num, n.share_num
            FROM perception_cls_news n
            WHERE 1=1
        """
        params = []
        if start_time:
            query += " AND n.ctime >= %s"
            params.append(int(start_time.timestamp()))
        if end_time:
            query += " AND n.ctime <= %s"
            params.append(int(end_time.timestamp()))
        query += " ORDER BY n.ctime DESC"
        cursor.execute(query, params)
        news_results = cursor.fetchall()
        for news in news_results:
            subjects_query = """
                SELECT subject_name
                FROM perception_cls_news_subjects
                WHERE news_id = %s
            """
            cursor.execute(subjects_query, (news['id'],))
            news['subjects'] = [row['subject_name'] for row in cursor.fetchall()]
        return news_results
    except Error as e:
        st.error(f"查询失败: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

# 检查新闻是否属于某个分组
def belongs_to_groups(subjects, selected_groups):
    if not subjects and '其他' in selected_groups:
        return True
    for group in selected_groups:
        if any(subject in THEME_GROUPS.get(group, []) for subject in subjects):
            return True
    return False

# 获取分组显示（仅用于“分组”列）
def assign_group(subjects):
    if not subjects:
        return '其他'
    groups = []
    for group, themes in THEME_GROUPS.items():
        if any(subject in themes for subject in subjects):
            groups.append(group)
    return ', '.join(groups) if groups else '其他'

# 主程序
def main():
    st.title("🌍 YYTT滚动资讯")

    # 时间范围：默认当天
    default_date = datetime.now().date()
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("开始日期", default_date)
    with col2:
        end_date = st.date_input("结束日期", default_date)
    start_time = datetime.combine(start_date, datetime.min.time())
    end_time = datetime.combine(end_date, datetime.max.time())

    # 分页设置
    page_size = 20

    # 主题分组筛选器：默认选择除“股市”外的所有分组
    group_options = list(THEME_GROUPS.keys())
    default_groups = [g for g in group_options if g != '股市']
    selected_groups = st.multiselect("筛选分组", options=group_options, default=default_groups)

    # 检索内容或标签：默认空
    search_query = st_keyup("检索内容或标签", value="", debounce=300, key="search_keyup")

    # 获取所有数据
    all_news_data = fetch_news_with_subjects(start_time, end_time)
    if not all_news_data:
        st.warning("暂无数据可显示")
        return

    # 应用筛选
    filtered_data = all_news_data
    if selected_groups:
        filtered_data = [
            news for news in filtered_data
            if belongs_to_groups(news['subjects'], selected_groups)
        ]
    if search_query:
        filtered_data = [
            news for news in filtered_data
            if (search_query.lower() in news['content'].lower() or
                any(search_query.lower() in subj.lower() for subj in news['subjects']))
        ]

    # 计算记录数和总页数
    total_filtered = len(filtered_data)
    total_pages = (total_filtered + page_size - 1) // page_size if total_filtered > 0 else 1

    # 初始化和管理页码
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 1
    if 'prev_filters' not in st.session_state:
        st.session_state.prev_filters = None

    # 检测筛选条件变化
    current_filters = (start_date, end_date, tuple(selected_groups), search_query)
    if st.session_state.prev_filters != current_filters:
        st.session_state.current_page = 1
        st.session_state.prev_filters = current_filters

    # 显示记录数（表格上方靠右）
    st.markdown(
        f"<div style='text-align: right;'>共 {total_filtered} 条记录，当前第 {st.session_state.current_page}/{total_pages} 页</div>",
        unsafe_allow_html=True
    )

    # 获取当前页数据
    start_idx = (st.session_state.current_page - 1) * page_size
    end_idx = min(start_idx + page_size, total_filtered)
    current_page_data = filtered_data[start_idx:end_idx]

    # 显示表格
    if current_page_data:
        df = pd.DataFrame(current_page_data)
        df['ctime'] = pd.to_datetime(df['ctime'], unit='s').dt.tz_localize('UTC').dt.tz_convert(
            'Asia/Shanghai').dt.tz_localize(None)
        df['group'] = df['subjects'].apply(assign_group)
        df = df[['ctime', 'subjects', 'content', 'reading_num', 'comment_num', 'share_num', 'group']]
        df.columns = ['时间', '标签', '内容', '阅读数', '评论数', '分享数', '分组']
        st.dataframe(
            df,
            use_container_width=True,
            height=500,
            column_config={
                '时间': st.column_config.DatetimeColumn(width="medium"),
                '标签': st.column_config.ListColumn(width="medium"),
                '内容': st.column_config.TextColumn(width="large"),
                '阅读数': st.column_config.NumberColumn(width="small"),
                '评论数': st.column_config.NumberColumn(width="small"),
                '分享数': st.column_config.NumberColumn(width="small"),
                '分组': st.column_config.TextColumn(width="medium")
            }
        )
    else:
        st.info("没有符合条件的数据")

    # 分页按钮（上一页和下一页）
    col_prev, col_spacer, col_next = st.columns([1, 8, 1])  # Adjust the ratios as needed
    with col_prev:
        if st.button("⬅️ 上一页", disabled=(st.session_state.current_page <= 1), key="prev_page"):
            st.session_state.current_page -= 1
            st.rerun()  # 强制重新运行以更新页面
    with col_spacer:
        st.write("")  # Empty column to act as a spacer
    with col_next:
        if st.button("下一页 ➡️", disabled=(st.session_state.current_page >= total_pages), key="next_page"):
            st.session_state.current_page += 1
            st.rerun()  # 强制重新运行以更新页面

if __name__ == "__main__":
    main()