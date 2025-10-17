import streamlit as st
import pandas as pd
import json
import plotly.express as px
from collections import Counter
from matplotlib_venn import venn2
import matplotlib.pyplot as plt

# --- CONFIGURATION AND DATA LOADING ---
# Note: Use st.cache_data for functions that load data to prevent re-running on every interaction
@st.cache_data
def load_data():
    """Loads all JSON data and performs initial data structuring."""
    try:
        # Load trend data (Step 1)
        with open("datasets/WWTrends.json") as f:
            WW_trends = json.load(f)
        with open("datasets/USTrends.json") as f:
            US_trends = json.load(f)
        
        # Load tweets data (Step 4)
        with open("datasets/WeLoveTheEarth.json") as f:
            tweets = json.load(f)
            
    except FileNotFoundError:
        st.error("Data files not found. Ensure 'WWTrends.json', 'USTrends.json', and 'WeLoveTheEarth.json' are in a 'datasets' folder.")
        return None, None, None, None

    # Common Trends (Step 3)
    world_trends = set([trend['name'] for trend in WW_trends[0]['trends']])
    us_trends = set([trend['name'] for trend in US_trends[0]["trends"]])
    common_trends = world_trends.intersection(us_trends)

    # Prepare Tweet Activity DataFrame (Step 7 & 8)
    retweets_data = []
    for tweet in tweets:
        if 'retweeted_status' in tweet:
            retweets_data.append({
                'Retweets': tweet['retweet_count'], 
                'Favorites': tweet['retweeted_status']['favorite_count'],
                'Followers': tweet['retweeted_status']['user']['followers_count'],
                'ScreenName': tweet['retweeted_status']['user']['screen_name'],
                'Text': tweet['text'],
                'Lang': tweet['lang']
            })
    
    # Aggregate data by original ScreenName and Text
    df = pd.DataFrame(retweets_data)
    
    # Create the aggregated DataFrame for the table and charts
    # We group by ScreenName, Text, and Followers of the original tweeter
    df_agg = df.groupby(['ScreenName', 'Text', 'Followers']).agg(
        Total_Retweets=('Retweets', 'sum'),
        Total_Favorites=('Favorites', 'sum')
    ).reset_index()

    # Calculate Normalized Engagement Rate (Goal of Step 9)
    df_agg['Total_Engagement'] = df_agg['Total_Retweets'] + df_agg['Total_Favorites']
    df_agg['Normalized_Engagement_Rate'] = (df_agg['Total_Engagement'] / df_agg['Followers']) * 100
    df_agg = df_agg.sort_values(by='Followers', ascending=False)
    
    # Language Data (Step 9)
    lang_counts = pd.DataFrame(Counter(df['Lang']).most_common(), columns=['Lang', 'Count'])

    return world_trends, us_trends, common_trends, df_agg, lang_counts

# --- VISUALIZATION FUNCTIONS ---

def create_venn_diagram(world_trends, us_trends, common_trends):
    """Creates a Matplotlib Venn Diagram for Trend Overlap (Interactive is hard for Venn)."""
    st.subheader("Interactive Common Trends Visualization")
    st.markdown("This Venn diagram shows the overlap between the **WorldWide** and **US** Top 50 trends.")
    
    # Matplotlib setup for Streamlit
    fig, ax = plt.subplots()
    
    # Calculate sizes for the Venn diagram
    size_ww_only = len(world_trends) - len(common_trends)
    size_us_only = len(us_trends) - len(common_trends)
    size_common = len(common_trends)
    
    # Generate Venn diagram
    venn2(subsets=(size_ww_only, size_us_only, size_common), 
          set_labels=('WW Trends', 'US Trends'),
          ax=ax)
    ax.set_title(f"WW & US Trend Overlap: {size_common} Common Topics")
    
    st.pyplot(fig)
    
    with st.expander("Common Trends List"):
        st.write(list(common_trends))

def create_engagement_scatter(df_agg):
    """Creates an interactive Plotly Scatter Plot for Tweet Activity."""
    st.subheader("Tweet Activity: Retweets vs. Favorites")
    st.markdown("Bubble size represents the original tweeter's **Followers** (log scale). Hover for details.")

    # Plotly Scatter Plot (Bubble Chart)
    fig = px.scatter(
        df_agg,
        x='Total_Retweets',
        y='Total_Favorites',
        size='Followers',
        color='ScreenName',
        hover_name='ScreenName',
        log_x=True,
        log_y=True,
        size_max=80,
        template='plotly_white',
        title='Engagement by Celebrity (Log-Log Scale)'
    )
    
    # Enhance tooltips to show key information
    fig.update_traces(
        hovertemplate="<b>%{hovertext}</b><br><br>" +
                      "Followers: %{marker.size:,}<br>" +
                      "Total Retweets: %{x:,}<br>" +
                      "Total Favorites: %{y:,}<br>" +
                      "<extra></extra>"
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
def create_engagement_bar_chart(df_agg):
    """Creates an interactive Plotly Bar Chart for Normalized Engagement."""
    st.subheader("Normalized Engagement Rate")
    st.markdown("Shows engagement as $\\frac{\\text{Retweets} + \\text{Favorites}}{\\text{Followers}}$ (x100). Highlights **Lil Dicky's** high relative success.")
    
    # Sort by Normalized Engagement Rate for the bar chart
    df_chart = df_agg.sort_values(by='Normalized_Engagement_Rate', ascending=False)
    
    fig = px.bar(
        df_chart,
        x='ScreenName',
        y='Normalized_Engagement_Rate',
        color='ScreenName',
        hover_data=['Followers', 'Total_Retweets', 'Total_Favorites'],
        template='plotly_white',
        title='Relative Engagement Success by Tweeter'
    )
    fig.update_layout(xaxis={'categoryorder':'total descending'})
    st.plotly_chart(fig, use_container_width=True)

def create_language_map_and_chart(lang_counts):
    """Creates a Choropleth map (using a simplified mapping) and a Bar Chart for language distribution."""
    st.subheader("Trend Global Reach: Language Distribution")
    
    # Simple Lang to Country Code Mapping for Plotly Choropleth
    # Plotly's choropleth needs ISO-3 or ISO-2 country codes. We use a simple map of major languages.
    lang_to_country = {
        'en': 'USA', # Plotly uses Country Names or ISO codes
        'es': 'Spain',
        'it': 'Italy',
        'pl': 'Poland',
        'ja': 'Japan',
        'fr': 'France',
        'de': 'Germany',
        'tr': 'Turkey', # assuming 'tr' for Turkish
        'ru': 'Russia',
        'ko': 'South Korea'
        # 'und' (undetermined) and others are hard to map to a single country, so we focus on the major ones.
    }
    
    # Filter and map data for the map
    df_map = lang_counts[lang_counts['Lang'].isin(lang_to_country.keys())].copy()
    df_map['Country'] = df_map['Lang'].map(lang_to_country)
    
    st.markdown("### Choropleth Map (Simplified)")
    st.markdown("Map colors show the count of tweets for the **major** languages in the dataset, mapped to their primary country. This gives a visual sense of global discussion.")

    # Create the Choropleth Map
    fig_map = px.choropleth(
        df_map,
        locations='Country',
        locationmode='country names', # Instruct Plotly to use country names
        color='Count',
        hover_name='Country',
        color_continuous_scale=px.colors.sequential.Plasma,
        title='Tweet Language Distribution by Country (Top Languages)',
        template='plotly_white'
    )
    fig_map.update_layout(margin={"r":0,"t":50,"l":0,"b":0})
    st.plotly_chart(fig_map, use_container_width=True)

    st.markdown("### Full Language Count Bar Chart")
    st.markdown("The bar chart includes all language codes, including **'und' (undetermined)**, which accounted for a large volume of tweets.")

    # Create the Language Bar Chart (Full data)
    fig_bar = px.bar(
        lang_counts,
        x='Lang',
        y='Count',
        color='Lang',
        title='Full Distribution of Tweet Languages',
        template='plotly_white'
    )
    fig_bar.update_layout(xaxis={'categoryorder':'total descending'})
    st.plotly_chart(fig_bar, use_container_width=True)


# --- STREAMLIT APP LAYOUT ---

def main():
    st.set_page_config(layout="wide", page_title="Twitter Trend Dynamics: #WeLoveTheEarth")

    st.title("🌎 Twitter Trend Dynamics: #WeLoveTheEarth")
    st.markdown("An interactive analysis of the **Local and Global** thought patterns around a viral trend, built for a Data Science portfolio.")
    st.info("The data analysis reveals that while major celebrities have huge follower counts, **Lil Dicky** achieved the highest *relative* engagement rate with his tweet for the Earth Day music video.")
    
    # Load all processed data
    world_trends, us_trends, common_trends, df_agg, lang_counts = load_data()

    if world_trends is None:
        return # Stop execution if data loading failed

    # --- SECTION 1: Trend Overlap ---
    st.header("1. Global vs. Local Trend Overlap")
    create_venn_diagram(world_trends, us_trends, common_trends)

    st.markdown("---")

    # --- SECTION 2: Engagement Analysis ---
    st.header("2. Celebrity Activity & Engagement")
    st.dataframe(
        df_agg[['ScreenName', 'Followers', 'Total_Retweets', 'Total_Favorites', 'Normalized_Engagement_Rate', 'Text']].head(10)
        .style.background_gradient(cmap='Greens', subset=['Normalized_Engagement_Rate'])
        .format({'Followers': '{:,}', 'Total_Retweets': '{:,}', 'Total_Favorites': '{:,}', 'Normalized_Engagement_Rate': '{:.4f}%'})
    )
    
    col1, col2 = st.columns(2)
    with col1:
        create_engagement_scatter(df_agg)
    with col2:
        create_engagement_bar_chart(df_agg)

    st.markdown("---")

    # --- SECTION 3: Global Language Reach ---
    st.header("3. Global Language Reach")
    create_language_map_and_chart(lang_counts)

    st.markdown("---")
    st.caption("Project built using Python, Pandas, Plotly, and Streamlit.")


if __name__ == "__main__":
    main()