"""
visualizer.py — Auto-detects the best chart type and creates a Plotly figure.
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def auto_visualize(df: pd.DataFrame, question: str = ""):
    """
    Intelligently select and create a chart from a query result DataFrame.
    Returns a Plotly figure or None if chart is not appropriate.
    """
    if df is None or df.empty or len(df.columns) < 1:
        return None

    # Single value — no chart needed
    if df.shape == (1, 1):
        return None

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    text_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

    chart_title = _infer_title(question)

    # ── Case 1: One text + one numeric → Bar chart ─────────────────────────────
    if len(text_cols) >= 1 and len(numeric_cols) >= 1:
        x_col = text_cols[0]
        y_col = numeric_cols[0]

        # If too many categories → horizontal bar
        if df[x_col].nunique() > 10:
            fig = px.bar(
                df.head(20), x=y_col, y=x_col, orientation="h",
                title=chart_title,
                color=y_col,
                color_continuous_scale="emrld",
                labels={x_col: x_col.replace("_", " ").title(),
                        y_col: y_col.replace("_", " ").title()}
            )
        else:
            fig = px.bar(
                df, x=x_col, y=y_col,
                title=chart_title,
                color=y_col,
                color_continuous_scale="emrld",
                labels={x_col: x_col.replace("_", " ").title(),
                        y_col: y_col.replace("_", " ").title()}
            )
        fig = _style_chart(fig)
        return fig

    # ── Case 2: Only numeric columns → line or multi-bar ─────────────────────
    if len(numeric_cols) >= 2 and len(text_cols) == 0:
        fig = px.line(df, title=chart_title)
        fig = _style_chart(fig)
        return fig

    # ── Case 3: Single numeric column → histogram ─────────────────────────────
    if len(numeric_cols) == 1 and len(text_cols) == 0:
        fig = px.histogram(
            df, x=numeric_cols[0],
            title=chart_title,
            color_discrete_sequence=["#10B981"]
        )
        fig = _style_chart(fig)
        return fig

    # ── Case 4: Two text columns only → count bar ─────────────────────────────
    if len(text_cols) >= 1 and len(numeric_cols) == 0:
        x_col = text_cols[0]
        counts = df[x_col].value_counts().reset_index()
        counts.columns = [x_col, "count"]
        fig = px.bar(
            counts, x=x_col, y="count",
            title=chart_title,
            color="count",
            color_continuous_scale="emrld"
        )
        fig = _style_chart(fig)
        return fig

    return None


def _style_chart(fig):
    """Apply consistent dark theme styling to all charts."""
    fig.update_layout(
        paper_bgcolor="#050508",
        plot_bgcolor="#050508",
        font=dict(color="#E2E8F0", family="Inter, sans-serif", size=13),
        title_font=dict(size=18, color="#10B981"),
        xaxis=dict(gridcolor="#1F2937", tickfont=dict(color="#94A3B8")),
        yaxis=dict(gridcolor="#1F2937", tickfont=dict(color="#94A3B8")),
        coloraxis_showscale=False,
        margin=dict(l=40, r=40, t=60, b=40),
        hoverlabel=dict(bgcolor="#0D0E12", font_color="#E2E8F0"),
    )
    return fig


def _infer_title(question: str) -> str:
    """Generate a chart title from the user's question."""
    if not question:
        return "Query Results"
    # Capitalize and truncate
    title = question.strip().rstrip("?").capitalize()
    return title[:70] + "..." if len(title) > 70 else title
