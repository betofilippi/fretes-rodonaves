#!/usr/bin/env python3
"""
Final verification script for distance data in the Rodonaves freight system.
"""

import sys
import os
from sqlmodel import Session, select, func, text

# Add the app directory to Python path
sys.path.append(os.path.dirname(__file__))

try:
    from frete_app.db import engine
    from frete_app.models_extended import (
        Estado, FilialRodonaves, CidadeRodonaves
    )
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

def verify_distance_data():
    """Verify distance data comprehensively"""
    print("RODONAVES DISTANCE VERIFICATION REPORT")
    print("=" * 60)

    session = Session(engine)

    try:
        # 1. Basic Overview
        print("\n1. DATABASE OVERVIEW")
        print("-" * 30)

        total_states = session.exec(select(func.count(Estado.id))).first()
        total_cities = session.exec(select(func.count(CidadeRodonaves.id))).first()
        total_filiais = session.exec(select(func.count(FilialRodonaves.id))).first()

        print(f"Total States: {total_states}")
        print(f"Total Cities: {total_cities}")
        print(f"Total Filiais: {total_filiais}")

        # 2. Distance Statistics
        print("\n2. DISTANCE DATA STATISTICS")
        print("-" * 30)

        valid_distances = session.exec(
            select(func.count(CidadeRodonaves.id))
            .where(CidadeRodonaves.distancia_km > 0)
        ).first()

        zero_distances = session.exec(
            select(func.count(CidadeRodonaves.id))
            .where(CidadeRodonaves.distancia_km == 0)
        ).first()

        null_distances = session.exec(
            select(func.count(CidadeRodonaves.id))
            .where(CidadeRodonaves.distancia_km.is_(None))
        ).first()

        print(f"Cities with valid distances (> 0): {valid_distances}")
        print(f"Cities with zero distances (filial): {zero_distances}")
        print(f"Cities with null distances (missing): {null_distances}")

        if total_cities > 0:
            coverage = ((valid_distances + zero_distances) / total_cities) * 100
            print(f"Distance coverage: {coverage:.2f}%")

        # 3. Major Capitals - let's search by pattern
        print("\n3. MAJOR CAPITALS VERIFICATION")
        print("-" * 30)

        capitals_to_find = ['São Paulo', 'Rio de Janeiro', 'Belo Horizonte', 'Curitiba', 'Porto Alegre', 'Florianópolis']

        for capital in capitals_to_find:
            # Try different variations of the name
            variations = [capital, capital.upper(), capital.lower()]
            found = False

            for variation in variations:
                cities = session.exec(
                    select(CidadeRodonaves, Estado.sigla, FilialRodonaves.codigo)
                    .join(Estado)
                    .join(FilialRodonaves, CidadeRodonaves.filial_atendimento_id == FilialRodonaves.id)
                    .where(CidadeRodonaves.nome.like(f'%{variation}%'))
                ).all()

                if cities:
                    for city, state_sigla, filial_code in cities[:1]:  # Show first match
                        distance_str = f"{city.distancia_km}km" if city.distancia_km is not None else "No distance"
                        print(f"{city.nome}/{state_sigla}: {distance_str} (via {filial_code}) - {city.categoria_tarifa}")
                        found = True
                        break

            if not found:
                print(f"{capital}: Not found")

        # 4. State Coverage
        print("\n4. STATE COVERAGE SUMMARY")
        print("-" * 30)

        states = session.exec(select(Estado).order_by(Estado.sigla)).all()

        for state in states:
            # Simple count queries
            total_cities_in_state = session.exec(
                select(func.count(CidadeRodonaves.id))
                .where(CidadeRodonaves.estado_id == state.id)
            ).first()

            cities_with_distance = session.exec(
                select(func.count(CidadeRodonaves.id))
                .where(CidadeRodonaves.estado_id == state.id)
                .where(CidadeRodonaves.distancia_km.is_not(None))
            ).first()

            if total_cities_in_state > 0:
                coverage_pct = (cities_with_distance / total_cities_in_state) * 100
                print(f"{state.sigla:2} ({state.nome:15}): {total_cities_in_state:4} cities, {coverage_pct:6.1f}% coverage")

        # 5. Sample distances from different states
        print("\n5. SAMPLE DISTANCES BY STATE")
        print("-" * 30)

        for state in states[:8]:  # First 8 states
            sample_city = session.exec(
                select(CidadeRodonaves, FilialRodonaves.codigo)
                .join(FilialRodonaves, CidadeRodonaves.filial_atendimento_id == FilialRodonaves.id)
                .where(CidadeRodonaves.estado_id == state.id)
                .where(CidadeRodonaves.distancia_km > 0)
                .limit(1)
            ).first()

            if sample_city:
                city, filial_code = sample_city
                print(f"{state.sigla} - {city.nome}: {city.distancia_km}km (via {filial_code}) - {city.categoria_tarifa}")

        # 6. Filial verification
        print("\n6. FILIAL CITIES VERIFICATION (Sample)")
        print("-" * 30)

        filiais = session.exec(select(FilialRodonaves).limit(10)).all()

        for filial in filiais:
            # Find city with same name as filial
            filial_city = session.exec(
                select(CidadeRodonaves)
                .where(CidadeRodonaves.nome == filial.cidade)
                .where(CidadeRodonaves.estado_id == filial.estado_id)
            ).first()

            if filial_city:
                distance = filial_city.distancia_km
                status = "OK" if distance == 0 else "WARNING"
                print(f"{filial.codigo:3} ({filial.cidade:15}): {distance}km - {status}")
            else:
                print(f"{filial.codigo:3} ({filial.cidade:15}): City not found in database")

        # 7. Distance ranges by state
        print("\n7. DISTANCE RANGES BY STATE")
        print("-" * 30)

        for state in states[:5]:  # First 5 states
            result = session.exec(
                select(
                    func.min(CidadeRodonaves.distancia_km),
                    func.max(CidadeRodonaves.distancia_km),
                    func.avg(CidadeRodonaves.distancia_km)
                )
                .where(CidadeRodonaves.estado_id == state.id)
                .where(CidadeRodonaves.distancia_km > 0)
            ).first()

            if result and result[0] is not None:
                min_dist, max_dist, avg_dist = result
                print(f"{state.sigla}: {min_dist:.0f}km - {max_dist:.0f}km (avg: {avg_dist:.0f}km)")

        # 8. Anomaly detection
        print("\n8. ANOMALY DETECTION")
        print("-" * 30)

        # Very high distances
        high_distances = session.exec(
            select(CidadeRodonaves.nome, Estado.sigla, CidadeRodonaves.distancia_km)
            .join(Estado)
            .where(CidadeRodonaves.distancia_km > 2500)
            .limit(5)
        ).all()

        if high_distances:
            print("Cities with very high distances (>2500km):")
            for city_name, state_sigla, distance in high_distances:
                print(f"  {city_name}/{state_sigla}: {distance}km")
        else:
            print("No cities with suspiciously high distances found")

        # Check for missing distance data
        states_with_missing = []
        for state in states:
            missing_count = session.exec(
                select(func.count(CidadeRodonaves.id))
                .where(CidadeRodonaves.estado_id == state.id)
                .where(CidadeRodonaves.distancia_km.is_(None))
            ).first()

            if missing_count > 0:
                states_with_missing.append(f"{state.sigla}: {missing_count}")

        if states_with_missing:
            print("States with missing distance data:")
            for state_info in states_with_missing:
                print(f"  {state_info}")
        else:
            print("All states have complete distance data")

        # 9. Final Assessment
        print("\n9. FINAL ASSESSMENT")
        print("-" * 30)

        if total_cities > 0:
            coverage = ((valid_distances + zero_distances) / total_cities) * 100

            print(f"Total cities in database: {total_cities}")
            print(f"Cities with distance data: {valid_distances + zero_distances}")
            print(f"Coverage rate: {coverage:.2f}%")
            print(f"Valid distances (> 0): {valid_distances}")
            print(f"Zero distances (filial cities): {zero_distances}")
            print(f"Null/missing distances: {null_distances}")

            if coverage >= 99:
                status = "EXCELLENT"
                message = "Distance data is comprehensive and well-imported"
            elif coverage >= 95:
                status = "VERY GOOD"
                message = "Distance data coverage is very good with minimal gaps"
            elif coverage >= 85:
                status = "GOOD"
                message = "Distance data coverage is adequate with minor gaps"
            elif coverage >= 70:
                status = "FAIR"
                message = "Distance data has significant gaps that should be addressed"
            else:
                status = "POOR"
                message = "Distance data coverage is insufficient"

            print(f"\nOverall Status: {status}")
            print(f"Assessment: {message}")

            # Check if distances are realistic (local filial-to-city, not total route)
            if valid_distances > 0:
                avg_distance_all = session.exec(
                    select(func.avg(CidadeRodonaves.distancia_km))
                    .where(CidadeRodonaves.distancia_km > 0)
                ).first()

                if avg_distance_all:
                    print(f"Average distance across all cities: {avg_distance_all:.0f}km")
                    if avg_distance_all < 500:
                        print("✓ Average distance suggests local filial-to-city distances")
                    else:
                        print("⚠ Average distance might indicate total route distances")

    except Exception as e:
        print(f"Error during verification: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")

if __name__ == "__main__":
    verify_distance_data()