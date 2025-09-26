#!/usr/bin/env python3
"""
Comprehensive verification script for distance data in the Rodonaves freight system.
Checks all cities, states, and validates distance calculations.
"""

import sys
import os
from sqlmodel import Session, select, func

# Add the app directory to Python path
sys.path.append(os.path.dirname(__file__))

try:
    from frete_app.db import engine
    from frete_app.models_extended import (
        Estado, FilialRodonaves, CidadeRodonaves
    )
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running from the project root directory")
    sys.exit(1)

def verify_distance_data():
    """Verify distance data comprehensively"""
    print("RODONAVES DISTANCE VERIFICATION REPORT")
    print("=" * 60)

    session = Session(engine)

    try:
        # Basic counts
        print("\n1. DATABASE OVERVIEW")
        print("-" * 30)

        total_states = session.exec(select(func.count(Estado.id))).first()
        total_cities = session.exec(select(func.count(CidadeRodonaves.id))).first()
        total_filiais = session.exec(select(func.count(FilialRodonaves.id))).first()

        print(f"Total States: {total_states}")
        print(f"Total Cities: {total_cities}")
        print(f"Total Filiais: {total_filiais}")

        # Distance statistics
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

        # Major capitals verification
        print("\n3. MAJOR CAPITALS VERIFICATION")
        print("-" * 30)

        major_capitals = [
            ('São Paulo', 'SP'),
            ('Rio de Janeiro', 'RJ'),
            ('Belo Horizonte', 'MG'),
            ('Curitiba', 'PR'),
            ('Porto Alegre', 'RS'),
            ('Florianópolis', 'SC')
        ]

        for city_name, state_abbr in major_capitals:
            try:
                state = session.exec(
                    select(Estado).where(Estado.sigla == state_abbr)
                ).first()

                if state:
                    city = session.exec(
                        select(CidadeRodonaves)
                        .where(CidadeRodonaves.nome == city_name)
                        .where(CidadeRodonaves.estado_id == state.id)
                    ).first()

                    if city:
                        filial = session.exec(
                            select(FilialRodonaves).where(FilialRodonaves.id == city.filial_atendimento_id)
                        ).first()

                        filial_code = filial.codigo if filial else "Unknown"
                        distance_str = f"{city.distancia_km}km" if city.distancia_km is not None else "No distance"

                        print(f"{city_name}/{state_abbr}: {distance_str} (via {filial_code}) - {city.categoria_tarifa}")
                    else:
                        print(f"{city_name}/{state_abbr}: City not found")
                else:
                    print(f"{city_name}/{state_abbr}: State not found")
            except Exception as e:
                print(f"{city_name}/{state_abbr}: Error - {e}")

        # State-by-state summary
        print("\n4. STATE COVERAGE SUMMARY")
        print("-" * 30)

        states = session.exec(select(Estado).order_by(Estado.sigla)).all()

        for state in states:
            state_stats = session.exec(
                select(
                    func.count(CidadeRodonaves.id).label('total'),
                    func.sum(
                        func.case(
                            (CidadeRodonaves.distancia_km > 0, 1),
                            (CidadeRodonaves.distancia_km == 0, 1),
                            else_=0
                        )
                    ).label('with_distance')
                )
                .where(CidadeRodonaves.estado_id == state.id)
            ).first()

            if state_stats.total > 0:
                coverage_pct = (state_stats.with_distance / state_stats.total) * 100 if state_stats.with_distance else 0
                print(f"{state.sigla:2} ({state.nome:15}): {state_stats.total:4} cities, {coverage_pct:6.1f}% coverage")

        # Filial cities verification
        print("\n5. FILIAL CITIES VERIFICATION")
        print("-" * 30)

        filiais = session.exec(select(FilialRodonaves).order_by(FilialRodonaves.codigo)).all()

        for filial in filiais[:10]:  # Show first 10 filiais
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
                print(f"{filial.codigo:3} ({filial.cidade:15}): City not found")

        # Sample distances for validation
        print("\n6. SAMPLE DISTANCES FOR VALIDATION")
        print("-" * 30)

        # Get some random cities with distances
        sample_cities = session.exec(
            select(CidadeRodonaves, Estado.sigla, FilialRodonaves.codigo)
            .join(Estado)
            .join(FilialRodonaves, CidadeRodonaves.filial_atendimento_id == FilialRodonaves.id)
            .where(CidadeRodonaves.distancia_km > 0)
            .limit(15)
        ).all()

        for city, state_sigla, filial_code in sample_cities:
            print(f"{city.nome}/{state_sigla}: {city.distancia_km}km (via {filial_code}) - {city.categoria_tarifa}")

        # Anomaly detection
        print("\n7. ANOMALY DETECTION")
        print("-" * 30)

        # Very high distances
        high_distances = session.exec(
            select(CidadeRodonaves, Estado.sigla)
            .join(Estado)
            .where(CidadeRodonaves.distancia_km > 2500)
        ).all()

        if high_distances:
            print("Cities with very high distances (>2500km):")
            for city, state_sigla in high_distances[:5]:
                print(f"  {city.nome}/{state_sigla}: {city.distancia_km}km")
        else:
            print("No cities with suspiciously high distances found")

        # Negative distances
        negative_distances = session.exec(
            select(CidadeRodonaves, Estado.sigla)
            .join(Estado)
            .where(CidadeRodonaves.distancia_km < 0)
        ).all()

        if negative_distances:
            print("Cities with negative distances:")
            for city, state_sigla in negative_distances:
                print(f"  {city.nome}/{state_sigla}: {city.distancia_km}km")
        else:
            print("No cities with negative distances found")

        # Final assessment
        print("\n8. FINAL ASSESSMENT")
        print("-" * 30)

        if total_cities > 0:
            coverage = ((valid_distances + zero_distances) / total_cities) * 100

            if coverage >= 95:
                status = "EXCELLENT"
                message = "Distance data is comprehensive and well-imported"
            elif coverage >= 85:
                status = "GOOD"
                message = "Distance data coverage is adequate with minor gaps"
            elif coverage >= 70:
                status = "FAIR"
                message = "Distance data has significant gaps that should be addressed"
            else:
                status = "POOR"
                message = "Distance data coverage is insufficient"

            print(f"Overall Status: {status}")
            print(f"Assessment: {message}")
            print(f"Coverage Rate: {coverage:.2f}%")
        else:
            print("No cities found in database")

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