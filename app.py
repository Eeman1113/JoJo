import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import re

# Function to extract salary range and convert to numeric
def process_salary(salary_range):
    # Extract numbers from LPA format
    numbers = re.findall(r'(\d+(?:\.\d+)?)', str(salary_range))
    if len(numbers) >= 2:
        min_salary = float(numbers[0])
        max_salary = float(numbers[1])
        avg_salary = (min_salary + max_salary) / 2
        return pd.Series({'min_salary': min_salary, 'max_salary': max_salary, 'avg_salary': avg_salary})
    return pd.Series({'min_salary': None, 'max_salary': None, 'avg_salary': None})

# Function to extract years from experience
def process_experience(exp):
    numbers = re.findall(r'(\d+(?:\.\d+)?)', str(exp))
    if len(numbers) >= 2:
        return (float(numbers[0]) + float(numbers[1])) / 2
    elif len(numbers) == 1:
        return float(numbers[0])
    return None

# Set page config
st.set_page_config(page_title="Indian Job Market Analysis", layout="wide", initial_sidebar_state="expanded")

# Load and preprocess data
@st.cache_data
def load_data():
    df = pd.read_csv('./india_job_market_dataset.csv')
    
    # Process salary data
    salary_info = df['Salary Range'].apply(process_salary)
    df = pd.concat([df, salary_info], axis=1)
    
    # Process experience
    df['Experience_Years'] = df['Experience Required'].apply(process_experience)
    
    # Convert dates
    df['Posted_Date'] = pd.to_datetime(df['Posted Date'])
    df['Application_Deadline'] = pd.to_datetime(df['Application Deadline'])
    
    # Process skills
    df['Skills_List'] = df['Skills Required'].str.split(',')
    
    return df

# Load data
try:
    df = load_data()
except Exception as e:
    st.error(f"Error loading data: {str(e)}")
    st.stop()

# Dashboard Title and Description
st.title("🎯 Indian Job Market Analysis")
st.markdown("""
This dashboard provides comprehensive insights into the Indian job market, including salary trends,
skill demands, and company-wise analysis. Use the filters in the sidebar to customize your view.
""")
st.markdown("---")

# Sidebar filters
with st.sidebar:
    st.header("Filters")
    
    # Date range filter
    date_range = st.date_input(
        "Select Date Range",
        value=(df['Posted_Date'].min(), df['Posted_Date'].max()),
        key="date_range",
    )
    
    # Location filter
    selected_locations = st.multiselect(
        "Select Locations",
        options=sorted(df['Job Location'].unique()),
        default=sorted(df['Job Location'].unique())[:5]
    )
    
    # Company size filter
    selected_sizes = st.multiselect(
        "Company Size",
        options=sorted(df['Company Size'].unique()),
        default=sorted(df['Company Size'].unique())
    )
    
    # Job type filter
    selected_types = st.multiselect(
        "Job Type",
        options=sorted(df['Job Type'].unique()),
        default=sorted(df['Job Type'].unique())
    )

# Apply filters
mask = (
    (df['Posted_Date'].dt.date >= date_range[0]) &
    (df['Posted_Date'].dt.date <= date_range[1]) &
    (df['Job Location'].isin(selected_locations)) &
    (df['Company Size'].isin(selected_sizes)) &
    (df['Job Type'].isin(selected_types))
)
filtered_df = df[mask]

if filtered_df.empty:
    st.warning("No data available for the selected filters. Please adjust your selection.")
    st.stop()

# Key Metrics
st.header("📊 Key Metrics")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Total Jobs",
        f"{len(filtered_df):,}",
        f"{len(filtered_df) - len(df[~mask]):+,} from selection"
    )

with col2:
    avg_salary = filtered_df['avg_salary'].mean()
    st.metric(
        "Average Salary (LPA)",
        f"₹{avg_salary:.2f}",
        f"{(avg_salary - df['avg_salary'].mean()):.2f}"
    )

with col3:
    avg_exp = filtered_df['Experience_Years'].mean()
    st.metric(
        "Avg Experience Required",
        f"{avg_exp:.1f} years",
        f"{(avg_exp - df['Experience_Years'].mean()):.1f}"
    )

with col4:
    remote_pct = (filtered_df['Remote/Onsite'] == 'Remote').mean() * 100
    st.metric(
        "Remote Jobs",
        f"{remote_pct:.1f}%",
        f"{(remote_pct - (df['Remote/Onsite'] == 'Remote').mean() * 100):.1f}%"
    )

# Salary Analysis
st.header("💰 Salary Analysis")
col1, col2 = st.columns(2)

with col1:
    # Salary by Experience
    fig_salary_exp = px.scatter(
        filtered_df,
        x='Experience_Years',
        y='avg_salary',
        color='Job Type',
        size='Number of Applicants',
        hover_data=['Job Title', 'Company Name'],
        title='Salary vs Experience Correlation',
        labels={
            'Experience_Years': 'Years of Experience',
            'avg_salary': 'Average Salary (LPA)',
            'Job Type': 'Job Type'
        }
    )
    st.plotly_chart(fig_salary_exp, use_container_width=True)

with col2:
    # Salary by Location
    salary_by_loc = filtered_df.groupby('Job Location').agg({
        'avg_salary': ['mean', 'count']
    }).round(2)
    salary_by_loc.columns = ['Avg Salary', 'Job Count']
    
    fig_salary_loc = px.bar(
        salary_by_loc.reset_index(),
        x='Job Location',
        y='Avg Salary',
        color='Job Count',
        title='Average Salary by Location',
        labels={'Job Location': 'Location', 'Avg Salary': 'Average Salary (LPA)'}
    )
    st.plotly_chart(fig_salary_loc, use_container_width=True)

# Skills Analysis
st.header("🎯 Skills in Demand")
col1, col2 = st.columns(2)

with col1:
    # Top Skills
    all_skills = [skill.strip() for skills in filtered_df['Skills_List'] for skill in skills]
    skills_df = pd.DataFrame(all_skills, columns=['Skill']).value_counts().reset_index()
    skills_df.columns = ['Skill', 'Count']
    
    fig_skills = px.bar(
        skills_df.head(10),
        x='Count',
        y='Skill',
        orientation='h',
        title='Top 10 Most In-Demand Skills',
        labels={'Count': 'Number of Job Postings', 'Skill': 'Skill'}
    )
    st.plotly_chart(fig_skills, use_container_width=True)

with col2:
    # Skills by Average Salary
    skills_salary = filtered_df.explode('Skills_List')
    skills_salary_avg = skills_salary.groupby('Skills_List')['avg_salary'].agg(['mean', 'count']).round(2)
    skills_salary_avg = skills_salary_avg[skills_salary_avg['count'] >= 5].sort_values('mean', ascending=False)
    
    fig_skills_salary = px.bar(
        skills_salary_avg.head(10).reset_index(),
        x='Skills_List',
        y='mean',
        color='count',
        title='Top 10 Highest Paying Skills',
        labels={
            'Skills_List': 'Skill',
            'mean': 'Average Salary (LPA)',
            'count': 'Number of Jobs'
        }
    )
    st.plotly_chart(fig_skills_salary, use_container_width=True)

# Company Analysis
st.header("🏢 Company Insights")
col1, col2 = st.columns(2)

with col1:
    # Company Size vs Salary
    company_metrics = filtered_df.groupby('Company Size').agg({
        'avg_salary': 'mean',
        'Job ID': 'count',
        'Number of Applicants': 'mean'
    }).round(2)
    
    fig_company = go.Figure(data=[
        go.Bar(name='Avg Salary', y=company_metrics['avg_salary']),
        go.Bar(name='Avg Applicants', y=company_metrics['Number of Applicants'] / 50)  # Scaled for visualization
    ])
    
    fig_company.update_layout(
        title='Company Size Analysis',
        barmode='group',
        xaxis_title='Company Size',
        yaxis_title='Value'
    )
    st.plotly_chart(fig_company, use_container_width=True)

with col2:
    # Top Companies by Job Postings
    top_companies = filtered_df.groupby('Company Name').agg({
        'Job ID': 'count',
        'avg_salary': 'mean',
        'Number of Applicants': 'mean'
    }).sort_values('Job ID', ascending=False).head(10)
    
    fig_top_companies = px.scatter(
        top_companies.reset_index(),
        x='avg_salary',
        y='Number of Applicants',
        size='Job ID',
        color='Company Name',
        title='Top Companies Analysis',
        labels={
            'avg_salary': 'Average Salary (LPA)',
            'Number of Applicants': 'Average Applicants per Position',
            'Job ID': 'Number of Openings'
        }
    )
    st.plotly_chart(fig_top_companies, use_container_width=True)

# Job Market Trends
st.header("📈 Market Trends")
col1, col2 = st.columns(2)

with col1:
    # Time series of job postings
    daily_posts = filtered_df.groupby('Posted_Date').size().reset_index(name='count')
    fig_trends = px.line(
        daily_posts,
        x='Posted_Date',
        y='count',
        title='Daily Job Postings Trend',
        labels={'count': 'Number of Jobs Posted', 'Posted_Date': 'Date'}
    )
    st.plotly_chart(fig_trends, use_container_width=True)

with col2:
    # Education Requirements
    edu_dist = filtered_df['Education Requirement'].value_counts()
    fig_edu = px.pie(
        values=edu_dist.values,
        names=edu_dist.index,
        title='Distribution of Education Requirements'
    )
    st.plotly_chart(fig_edu, use_container_width=True)

# Interactive Job Search
st.header("🔍 Job Search")
search_cols = ['Job Title', 'Company Name', 'Job Location', 'Skills Required']
search_term = st.text_input("Search jobs by title, company, location, or skills")

if search_term:
    search_mask = pd.concat([
        filtered_df[col].str.contains(search_term, case=False, na=False)
        for col in search_cols
    ], axis=1).any(axis=1)
    search_results = filtered_df[search_mask]
else:
    search_results = filtered_df

# Display results in an interactive table
st.dataframe(
    search_results[[
        'Job Title', 'Company Name', 'Job Location', 'Job Type',
        'Salary Range', 'Experience Required', 'Posted_Date',
        'Remote/Onsite', 'Number of Applicants'
    ]].sort_values('Posted_Date', ascending=False),
    use_container_width=True,
    height=400
)

# Download button
csv = search_results.to_csv(index=False)
st.download_button(
    label="📥 Download Results as CSV",
    data=csv,
    file_name="job_search_results.csv",
    mime="text/csv"
)

# Footer
st.markdown("---")
st.markdown("""
💡 **Tips:**
- Use the filters in the sidebar to narrow down your search
- Click and drag on graphs to zoom in
- Double click to reset zoom
- Hover over data points for more information
""")