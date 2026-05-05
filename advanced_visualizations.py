"""
Advanced Visualization Module
Complex 3D visualizations, network graphs, and interactive charts
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import networkx as nx
from datetime import datetime


class AdvancedVisualizations:
    """Create advanced and interactive visualizations"""
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def create_3d_inventory_scatter(self):
        """Create 3D scatter plot of inventory metrics"""
        conn = self.db.get_connection()
        
        query = """
            SELECT drug_name, category, current_stock, unit_price,
                   minimum_stock, (current_stock * unit_price) as inventory_value
            FROM inventory
            WHERE current_stock > 0
            LIMIT 100
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if df.empty:
            return None
        
        fig = go.Figure(data=[go.Scatter3d(
            x=df['current_stock'],
            y=df['unit_price'],
            z=df['inventory_value'],
            mode='markers',
            marker=dict(
                size=8,
                color=df['inventory_value'],
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title="Value (₹)")
            ),
            text=df['drug_name'],
            hovertemplate='<b>%{text}</b><br>' +
                         'Stock: %{x}<br>' +
                         'Price: ₹%{y:.2f}<br>' +
                         'Value: ₹%{z:.2f}<extra></extra>'
        )])
        
        fig.update_layout(
            title='3D Inventory Analysis: Stock vs Price vs Value',
            scene=dict(
                xaxis_title='Current Stock (units)',
                yaxis_title='Unit Price (₹)',
                zaxis_title='Inventory Value (₹)'
            ),
            height=600
        )
        
        return fig
    
    def create_sankey_diagram(self):
        """Create Sankey diagram showing inventory flow"""
        conn = self.db.get_connection()
        
        query = """
            SELECT 
                i.category,
                CASE 
                    WHEN t.transaction_type = 'Sale' THEN 'Sales'
                    WHEN t.transaction_type = 'Dispose' THEN 'Wastage'
                    WHEN t.transaction_type = 'Expired' THEN 'Expired'
                    ELSE 'Other'
                END as destination,
                SUM(t.quantity) as quantity
            FROM transactions t
            JOIN inventory i ON t.drug_id = i.id
            WHERE DATE(t.created_at) >= DATE('now', '-90 days')
            GROUP BY i.category, destination
            HAVING quantity > 0
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if df.empty:
            return None
        
        # Prepare data for Sankey
        categories = df['category'].unique().tolist()
        destinations = df['destination'].unique().tolist()
        all_nodes = categories + destinations
        
        # Create node indices
        node_dict = {node: idx for idx, node in enumerate(all_nodes)}
        
        # Create links
        sources = [node_dict[cat] for cat in df['category']]
        targets = [node_dict[dest] for dest in df['destination']]
        values = df['quantity'].tolist()
        
        # Color mapping
        colors = ['#667eea', '#764ba2', '#f093fb', '#ff6b6b', '#4ecdc4', 
                 '#45b7d1', '#96ceb4', '#ffeaa7', '#dfe6e9', '#74b9ff']
        node_colors = [colors[i % len(colors)] for i in range(len(all_nodes))]
        
        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="black", width=0.5),
                label=all_nodes,
                color=node_colors
            ),
            link=dict(
                source=sources,
                target=targets,
                value=values,
                color='rgba(102, 126, 234, 0.4)'
            )
        )])
        
        fig.update_layout(
            title='Inventory Flow Analysis (Last 90 Days)',
            font=dict(size=12),
            height=500
        )
        
        return fig
    
    def create_sunburst_chart(self):
        """Create sunburst chart for hierarchical inventory view"""
        conn = self.db.get_connection()
        
        query = """
            SELECT category, drug_name, current_stock, (current_stock * unit_price) as value
            FROM inventory
            WHERE current_stock > 0
            LIMIT 100
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if df.empty:
            return None
        
        # Add root level
        df_sunburst = df.copy()
        df_sunburst['root'] = 'Total Inventory'
        
        fig = px.sunburst(
            df_sunburst,
            path=['root', 'category', 'drug_name'],
            values='value',
            title='Hierarchical Inventory Value Distribution',
            color='value',
            color_continuous_scale='RdYlGn',
            height=600
        )
        
        fig.update_traces(textinfo='label+percent parent')
        
        return fig
    
    def create_heatmap_consumption(self):
        """Create heatmap of consumption patterns"""
        conn = self.db.get_connection()
        
        query = """
            SELECT 
                i.category,
                CAST(strftime('%w', cp.date) AS INTEGER) as day_of_week,
                SUM(cp.quantity_consumed) as total_consumed
            FROM consumption_patterns cp
            JOIN inventory i ON cp.drug_id = i.id
            WHERE cp.date >= DATE('now', '-90 days')
            GROUP BY i.category, day_of_week
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if df.empty:
            return None
        
        # Pivot data for heatmap
        heatmap_data = df.pivot(index='category', columns='day_of_week', values='total_consumed')
        heatmap_data = heatmap_data.fillna(0)
        
        # Map day numbers to names
        day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        heatmap_data.columns = [day_names[int(col)] for col in heatmap_data.columns]
        
        fig = go.Figure(data=go.Heatmap(
            z=heatmap_data.values,
            x=heatmap_data.columns,
            y=heatmap_data.index,
            colorscale='Viridis',
            hovertemplate='Category: %{y}<br>Day: %{x}<br>Consumption: %{z}<extra></extra>'
        ))
        
        fig.update_layout(
            title='Consumption Heatmap by Category and Day of Week',
            xaxis_title='Day of Week',
            yaxis_title='Category',
            height=500
        )
        
        return fig
    
    def create_network_graph_drug_correlations(self, correlation_threshold=0.7):
        """Create network graph showing drug correlations"""
        conn = self.db.get_connection()
        
        query = """
            SELECT i1.drug_name as drug1, i2.drug_name as drug2,
                   cp1.date,
                   cp1.quantity_consumed as qty1,
                   cp2.quantity_consumed as qty2
            FROM consumption_patterns cp1
            JOIN consumption_patterns cp2 ON cp1.date = cp2.date AND cp1.drug_id < cp2.drug_id
            JOIN inventory i1 ON cp1.drug_id = i1.id
            JOIN inventory i2 ON cp2.drug_id = i2.id
            WHERE cp1.date >= DATE('now', '-180 days')
            LIMIT 5000
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if df.empty or len(df) < 10:
            return None
        
        # Calculate correlations
        correlations = []
        drug_pairs = df.groupby(['drug1', 'drug2'])
        
        for (drug1, drug2), group in drug_pairs:
            if len(group) >= 10:  # Need sufficient data points
                corr = np.corrcoef(group['qty1'], group['qty2'])[0, 1]
                if abs(corr) >= correlation_threshold:
                    correlations.append({
                        'drug1': drug1,
                        'drug2': drug2,
                        'correlation': corr
                    })
        
        if not correlations:
            return None
        
        # Create network graph
        G = nx.Graph()
        
        for corr_data in correlations[:30]:  # Limit to top 30 for visualization
            G.add_edge(
                corr_data['drug1'],
                corr_data['drug2'],
                weight=abs(corr_data['correlation'])
            )
        
        # Get positions using spring layout
        pos = nx.spring_layout(G, k=0.5, iterations=50)
        
        # Create edges
        edge_traces = []
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            
            weight = G[edge[0]][edge[1]]['weight']
            
            edge_trace = go.Scatter(
                x=[x0, x1, None],
                y=[y0, y1, None],
                mode='lines',
                line=dict(width=weight*3, color='rgba(102, 126, 234, 0.5)'),
                hoverinfo='none'
            )
            edge_traces.append(edge_trace)
        
        # Create nodes
        node_x = []
        node_y = []
        node_text = []
        
        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            node_text.append(node)
        
        node_trace = go.Scatter(
            x=node_x,
            y=node_y,
            mode='markers+text',
            text=node_text,
            textposition='top center',
            marker=dict(
                size=15,
                color='#667eea',
                line=dict(width=2, color='white')
            ),
            hovertemplate='<b>%{text}</b><extra></extra>'
        )
        
        # Create figure
        fig = go.Figure(data=edge_traces + [node_trace])
        
        fig.update_layout(
            title='Drug Correlation Network (Strong Correlations)',
            showlegend=False,
            hovermode='closest',
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            height=600
        )
        
        return fig
    
    def create_treemap_inventory_value(self):
        """Create treemap of inventory value by category and drug"""
        conn = self.db.get_connection()
        
        query = """
            SELECT category, drug_name, 
                   (current_stock * unit_price) as inventory_value,
                   current_stock
            FROM inventory
            WHERE current_stock > 0
            ORDER BY inventory_value DESC
            LIMIT 50
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if df.empty:
            return None
        
        fig = px.treemap(
            df,
            path=['category', 'drug_name'],
            values='inventory_value',
            title='Inventory Value Treemap',
            color='inventory_value',
            color_continuous_scale='Blues',
            hover_data={'current_stock': True}
        )
        
        fig.update_traces(
            textinfo='label+value',
            hovertemplate='<b>%{label}</b><br/>Value: ₹%{value:.2f}<br/>Stock: %{customdata[0]}<extra></extra>'
        )
        
        fig.update_layout(height=600)
        
        return fig
    
    def create_animated_trend_chart(self):
        """Create animated chart showing inventory trends over time"""
        conn = self.db.get_connection()
        
        query = """
            SELECT 
                DATE(cp.date) as date,
                i.category,
                SUM(cp.quantity_consumed) as total_consumed
            FROM consumption_patterns cp
            JOIN inventory i ON cp.drug_id = i.id
            WHERE cp.date >= DATE('now', '-90 days')
            GROUP BY DATE(cp.date), i.category
            ORDER BY date
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if df.empty:
            return None
        
        df['date'] = pd.to_datetime(df['date'])
        
        fig = px.line(
            df,
            x='date',
            y='total_consumed',
            color='category',
            title='Consumption Trends by Category (Last 90 Days)',
            labels={'total_consumed': 'Units Consumed', 'date': 'Date'},
            line_shape='spline'
        )
        
        fig.update_traces(mode='lines+markers')
        fig.update_layout(
            hovermode='x unified',
            height=500,
            xaxis=dict(showgrid=True, gridwidth=1, gridcolor='LightGray'),
            yaxis=dict(showgrid=True, gridwidth=1, gridcolor='LightGray')
        )
        
        return fig
