import json

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from neo4j import GraphDatabase
from pyvis.network import Network

# Neo4j connection details
NEO4J_URI = "neo4j+s://180596a7.databases.neo4j.io"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "WRq9EXby67ZU7Pf18B4K7Xs3nAtIGeBN8atM7okPpPQ"


def load_data(file):
    data = pd.read_csv(file)
    return data


def run_neo4j_query(query):
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session() as session:
        result = session.run(query)
        return result.data()


def draw_graph(data, selected_name):
    net = Network(height="600px", width="100%", bgcolor="#222222", font_color="white")

    # Add nodes and edges to the graph
    for record in data:
        path = record["path"]
        person1 = path[0]["Name"]
        person2 = path[-1]["Name"]
        ministry = record["Ministry"]
        overlap_start = record["OverlapStart"]
        overlap_end = record["OverlapEnd"]

        net.add_node(
            person1,
            label=person1,
            title=f"Worked at {ministry} from {overlap_start} to {overlap_end}",
            color="red" if person1 == selected_name else "blue",
        )
        net.add_node(
            person2,
            label=person2,
            title=f"Worked at {ministry} from {overlap_start} to {overlap_end}",
            color="red" if person2 == selected_name else "blue",
        )
        net.add_edge(
            person1,
            person2,
            title=f"Worked at {ministry} from {overlap_start} to {overlap_end}",
        )

    return net


def main():
    st.title("CSV Data Viewer")

    data = load_data("search_test_v4.csv")

    # Display the dataframe
    # st.write("### Data Preview")
    # st.dataframe(data)

    # Dropdown for name selection
    st.write("### Select a Name")
    names = data["Name"].unique()
    selected_name = st.selectbox("Select a name", names)

    # Filter data for the selected name
    selected_data = data[data["Name"] == selected_name].iloc[0]

    st.write("### Detailed View")
    st.write(selected_data)

    # Parse and display educational details
    edu_details = json.loads(selected_data["Education Qualifications"])
    st.write("### Educational Details")
    for edu in edu_details:
        st.markdown(
            f"**Degree:** {edu.get('degree', 'N/A')}, **Institute:** {edu.get('institute', 'N/A')}, **Subject:** {edu.get('subject', 'N/A')}, **Division:** {edu.get('division', 'N/A')}"
        )

    # Parse and display experience details
    exp_details = json.loads(selected_data["Experience Details"])
    st.write("### Experience Details")
    for i, exp in enumerate(exp_details):
        exp_str = f"""**Designation:** {exp.get('designation', 'N/A')}
        \n\n
        **Level:** {exp.get('level', 'N/A')}
        **Organisation:** {exp.get('organisation', 'N/A')}
        **Experience Major:** {exp.get('experience_major', 'N/A')}
        **Experience Minor:** {exp.get('experience_minor', 'N/A')}
        **Ministry:** {exp.get('ministry', 'N/A')}
        **Inferred Ministry:** {exp.get('inferred_ministry', 'N/A')}
        **Period From:** {exp.get('period_from', 'N/A')}
        **Period To:** {exp.get('period_to', 'N/A')}"""
        if st.button(exp_str, key=f"exp_{i}"):
            ministry = exp.get("inferred_ministry")
            if ministry is None:
                return

            ministry_name = ministry["ministry"]
            print(ministry_name)
            period_start = exp.get("period_from", "N/A")
            period_end = exp.get("period_to", "N/A")
            query = f"""  
            WITH "{ministry_name}" AS MINISTRY_NAME, datetime("{period_start}") AS PERIOD_START, datetime("{period_end}") AS PERIOD_END  
            MATCH path=(p1:Person)-[:EXPERIENCE]->(ex1:Experience)-[:WORKED_AT]->(m:Ministry)<-[:WORKED_AT]-(ex2:Experience)<-[:EXPERIENCE]-(p2:Person)  
            WHERE p1.Name = "{selected_name}" AND m.Ministry = MINISTRY_NAME AND ex1.From >= PERIOD_START AND ex2.To <= PERIOD_END  
            WITH m, p2, path, head(split(toString(CASE WHEN ex1.From > ex2.From THEN ex1.From ELSE ex2.From END), 'T')) AS OverlapStart, head(split(toString(CASE WHEN ex1.To < ex2.To THEN ex1.To ELSE ex2.To END), 'T')) AS OverlapEnd  
            RETURN DISTINCT path, m.Ministry as Ministry, OverlapStart, OverlapEnd, p2.Name AS Name  
            ORDER BY Name ASC  
            LIMIT 10  
            """
            results = run_neo4j_query(query)
            print(results)
            st.write(
                f"Query Results for {exp.get('designation', 'N/A')} at {exp.get('organisation', 'N/A')}:"
            )
            if results:
                net = draw_graph(results, selected_name)
                net_html = net.generate_html()
                components.html(net_html, height=600)
            else:
                st.write("No results found.")


if __name__ == "__main__":
    main()
