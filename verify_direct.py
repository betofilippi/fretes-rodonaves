#!/usr/bin/env python3
"""
Direct SQL verification script for distance data.
"""

import sqlite3
import os

def verify_distances():
    db_path = "frete.db"

    if not os.path.exists(db_path):
        print("Database file not found!")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("RODONAVES DISTANCE VERIFICATION REPORT")
    print("=" * 60)

    try:
        # 1. Basic counts
        print("\n1. DATABASE OVERVIEW")
        print("-" * 30)

        cursor.execute("SELECT COUNT(*) FROM estados")
        total_states = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM cidades_rodonaves")
        total_cities = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM filiais_rodonaves")
        total_filiais = cursor.fetchone()[0]

        print(f"Total States: {total_states}")
        print(f"Total Cities: {total_cities}")
        print(f"Total Filiais: {total_filiais}")

        # 2. Distance statistics
        print("\n2. DISTANCE DATA STATISTICS")
        print("-" * 30)

        cursor.execute("SELECT COUNT(*) FROM cidades_rodonaves WHERE distancia_km > 0")
        valid_distances = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM cidades_rodonaves WHERE distancia_km = 0")
        zero_distances = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM cidades_rodonaves WHERE distancia_km IS NULL")
        null_distances = cursor.fetchone()[0]

        print(f"Cities with valid distances (> 0): {valid_distances}")
        print(f"Cities with zero distances (filial): {zero_distances}")
        print(f"Cities with null distances (missing): {null_distances}")

        coverage = ((valid_distances + zero_distances) / total_cities) * 100 if total_cities > 0 else 0
        print(f"Distance coverage: {coverage:.2f}%")

        # 3. Major capitals check
        print("\n3. MAJOR CAPITALS VERIFICATION")
        print("-" * 30)

        # Check for capital cities
        capitals_query = """
        SELECT c.nome, e.sigla, c.distancia_km, c.categoria_tarifa, f.codigo
        FROM cidades_rodonaves c
        JOIN estados e ON c.estado_id = e.id
        JOIN filiais_rodonaves f ON c.filial_atendimento_id = f.id
        WHERE c.nome LIKE '%São Paulo%' OR c.nome LIKE '%Rio de Janeiro%'
           OR c.nome LIKE '%Belo Horizonte%' OR c.nome LIKE '%Curitiba%'
           OR c.nome LIKE '%Porto Alegre%' OR c.nome LIKE '%Florianópolis%'
        ORDER BY e.sigla, c.nome
        """

        cursor.execute(capitals_query)
        capitals = cursor.fetchall()

        if capitals:
            for city_name, state, distance, category, filial in capitals:
                distance_str = f"{distance}km" if distance is not None else "No distance"
                print(f"{city_name}/{state}: {distance_str} (via {filial}) - {category}")
        else:
            # Try alternative search
            cursor.execute("""
            SELECT c.nome, e.sigla, c.distancia_km, c.categoria_tarifa, f.codigo
            FROM cidades_rodonaves c
            JOIN estados e ON c.estado_id = e.id
            JOIN filiais_rodonaves f ON c.filial_atendimento_id = f.id
            WHERE e.sigla IN ('SP', 'RJ', 'MG', 'PR', 'RS', 'SC')
              AND c.categoria_tarifa = 'CAPITAL'
            ORDER BY e.sigla
            """)

            capital_cities = cursor.fetchall()
            for city_name, state, distance, category, filial in capital_cities:
                distance_str = f"{distance}km" if distance is not None else "No distance"
                print(f"{city_name}/{state}: {distance_str} (via {filial}) - {category}")

        # 4. State coverage
        print("\n4. STATE COVERAGE SUMMARY")
        print("-" * 30)

        cursor.execute("""
        SELECT e.sigla, e.nome,
               COUNT(c.id) as total_cities,
               COUNT(CASE WHEN c.distancia_km IS NOT NULL THEN 1 END) as with_distance
        FROM estados e
        LEFT JOIN cidades_rodonaves c ON e.id = c.estado_id
        GROUP BY e.id, e.sigla, e.nome
        ORDER BY e.sigla
        """)

        states_data = cursor.fetchall()
        for sigla, nome, total, with_distance in states_data:
            coverage_pct = (with_distance / total) * 100 if total > 0 else 0
            print(f"{sigla:2} ({nome:15}): {total:4} cities, {coverage_pct:6.1f}% coverage")

        # 5. Sample distances by state
        print("\n5. SAMPLE DISTANCES BY STATE")
        print("-" * 30)

        cursor.execute("""
        SELECT DISTINCT e.sigla, c.nome, c.distancia_km, c.categoria_tarifa, f.codigo
        FROM cidades_rodonaves c
        JOIN estados e ON c.estado_id = e.id
        JOIN filiais_rodonaves f ON c.filial_atendimento_id = f.id
        WHERE c.distancia_km > 0
        GROUP BY e.sigla
        ORDER BY e.sigla
        LIMIT 10
        """)

        samples = cursor.fetchall()
        for state, city, distance, category, filial in samples:
            print(f"{state} - {city}: {distance}km (via {filial}) - {category}")

        # 6. Filial cities verification (sample)
        print("\n6. FILIAL CITIES VERIFICATION (Sample)")
        print("-" * 30)

        cursor.execute("""
        SELECT f.codigo, f.cidade, c.distancia_km
        FROM filiais_rodonaves f
        LEFT JOIN cidades_rodonaves c ON f.cidade = c.nome AND f.estado_id = c.estado_id
        ORDER BY f.codigo
        LIMIT 15
        """)

        filial_check = cursor.fetchall()
        for codigo, cidade, distance in filial_check:
            if distance is not None:
                status = "OK" if distance == 0 else "WARNING"
                print(f"{codigo:3} ({cidade:15}): {distance}km - {status}")
            else:
                print(f"{codigo:3} ({cidade:15}): Not found in cities")

        # 7. Distance statistics by state
        print("\n7. DISTANCE RANGES BY STATE (Top 8)")
        print("-" * 30)

        cursor.execute("""
        SELECT e.sigla,
               MIN(c.distancia_km) as min_dist,
               MAX(c.distancia_km) as max_dist,
               AVG(c.distancia_km) as avg_dist,
               COUNT(CASE WHEN c.distancia_km > 0 THEN 1 END) as count_valid
        FROM estados e
        JOIN cidades_rodonaves c ON e.id = c.estado_id
        WHERE c.distancia_km > 0
        GROUP BY e.sigla
        ORDER BY e.sigla
        LIMIT 8
        """)

        ranges = cursor.fetchall()
        for sigla, min_dist, max_dist, avg_dist, count in ranges:
            print(f"{sigla}: {min_dist:.0f}km - {max_dist:.0f}km (avg: {avg_dist:.0f}km, n={count})")

        # 8. Anomaly detection
        print("\n8. ANOMALY DETECTION")
        print("-" * 30)

        # Very high distances
        cursor.execute("""
        SELECT c.nome, e.sigla, c.distancia_km
        FROM cidades_rodonaves c
        JOIN estados e ON c.estado_id = e.id
        WHERE c.distancia_km > 2500
        ORDER BY c.distancia_km DESC
        LIMIT 5
        """)

        high_distances = cursor.fetchall()
        if high_distances:
            print("Cities with very high distances (>2500km):")
            for city, state, distance in high_distances:
                print(f"  {city}/{state}: {distance}km")
        else:
            print("No cities with suspiciously high distances found")

        # Negative distances
        cursor.execute("""
        SELECT c.nome, e.sigla, c.distancia_km
        FROM cidades_rodonaves c
        JOIN estados e ON c.estado_id = e.id
        WHERE c.distancia_km < 0
        """)

        negative = cursor.fetchall()
        if negative:
            print("Cities with negative distances:")
            for city, state, distance in negative:
                print(f"  {city}/{state}: {distance}km")
        else:
            print("No cities with negative distances found")

        # Overall distance statistics
        cursor.execute("SELECT AVG(distancia_km) FROM cidades_rodonaves WHERE distancia_km > 0")
        avg_all = cursor.fetchone()[0]

        cursor.execute("SELECT MIN(distancia_km), MAX(distancia_km) FROM cidades_rodonaves WHERE distancia_km > 0")
        min_max = cursor.fetchone()

        print(f"Overall distance stats: {min_max[0]:.0f}km - {min_max[1]:.0f}km (avg: {avg_all:.0f}km)")

        # 9. Category distribution
        print("\n9. CITY CATEGORIES")
        print("-" * 30)

        cursor.execute("""
        SELECT categoria_tarifa, COUNT(*) as count,
               AVG(CASE WHEN distancia_km > 0 THEN distancia_km END) as avg_distance
        FROM cidades_rodonaves
        GROUP BY categoria_tarifa
        ORDER BY count DESC
        """)

        categories = cursor.fetchall()
        for category, count, avg_dist in categories:
            avg_str = f"{avg_dist:.0f}km" if avg_dist else "N/A"
            print(f"{category:12}: {count:4} cities (avg distance: {avg_str})")

        # 10. Final assessment
        print("\n10. FINAL ASSESSMENT")
        print("-" * 30)

        print(f"Total cities in database: {total_cities}")
        print(f"Cities with distance data: {valid_distances + zero_distances}")
        print(f"Coverage rate: {coverage:.2f}%")
        print(f"Valid distances (> 0): {valid_distances}")
        print(f"Zero distances (filial cities): {zero_distances}")
        print(f"Missing distances: {null_distances}")

        if coverage >= 99:
            status = "EXCELLENT"
            message = "Distance data is comprehensive and complete"
        elif coverage >= 95:
            status = "VERY GOOD"
            message = "Distance data coverage is very good with minimal gaps"
        elif coverage >= 85:
            status = "GOOD"
            message = "Distance data coverage is adequate"
        else:
            status = "NEEDS IMPROVEMENT"
            message = "Distance data has gaps that should be addressed"

        print(f"\nOverall Status: {status}")
        print(f"Assessment: {message}")

        if avg_all:
            print(f"Average distance: {avg_all:.0f}km")
            if avg_all < 500:
                print("✓ Distances appear to be local filial-to-city distances")
            else:
                print("⚠ Distances might be total route distances")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")

if __name__ == "__main__":
    verify_distances()