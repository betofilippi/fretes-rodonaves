#!/usr/bin/env python3
"""
Comprehensive verification script for distance data in the Rodonaves freight system.
Checks all cities, states, and validates distance calculations.
"""

import sys
import os
from sqlmodel import Session, select, func
from typing import Dict, List, Tuple, Optional
import pandas as pd

# Add the app directory to Python path
sys.path.append(os.path.dirname(__file__))

from frete_app.db import engine
from frete_app.models_extended import (
    Estado, FilialRodonaves, CidadeRodonaves,
    TaxaEspecial, CEPEspecial, TabelaTarifaCompleta
)

class DistanceVerificationReport:
    def __init__(self):
        self.session = Session(engine)
        self.report = {
            'total_states': 0,
            'total_cities': 0,
            'cities_with_valid_distances': 0,
            'cities_with_zero_distances': 0,
            'cities_with_null_distances': 0,
            'major_capitals_verification': {},
            'state_sample_verification': {},
            'distance_consistency_check': {},
            'filial_distance_verification': {},
            'anomalies': []
        }

    def run_verification(self) -> Dict:
        """Run comprehensive distance data verification"""
        print("Starting comprehensive distance verification...")

        try:
            self._verify_database_structure()
            self._count_basic_statistics()
            self._verify_major_capitals()
            self._sample_state_cities()
            self._check_distance_consistency()
            self._verify_filial_distances()
            self._analyze_anomalies()

            print("Verification completed successfully!")
            return self.report

        except Exception as e:
            print(f"Error during verification: {e}")
            self.report['error'] = str(e)
            return self.report
        finally:
            self.session.close()

    def _verify_database_structure(self):
        """Check if all required tables exist with data"""
        print("Verifying database structure...")

        # Check if tables have data
        states_count = self.session.exec(select(func.count(Estado.id))).first()
        cities_count = self.session.exec(select(func.count(CidadeRodonaves.id))).first()
        filiais_count = self.session.exec(select(func.count(FilialRodonaves.id))).first()

        print(f"   States: {states_count}")
        print(f"   Cities: {cities_count}")
        print(f"   Filiais: {filiais_count}")

        if states_count == 0:
            raise Exception("No states found in database")
        if cities_count == 0:
            raise Exception("No cities found in database")
        if filiais_count == 0:
            raise Exception("No filiais found in database")

    def _count_basic_statistics(self):
        """Count basic statistics about distance data"""
        print("📈 Counting basic statistics...")

        # Total counts
        self.report['total_states'] = self.session.exec(select(func.count(Estado.id))).first()
        self.report['total_cities'] = self.session.exec(select(func.count(CidadeRodonaves.id))).first()

        # Distance statistics
        valid_distances = self.session.exec(
            select(func.count(CidadeRodonaves.id))
            .where(CidadeRodonaves.distancia_km > 0)
        ).first()

        zero_distances = self.session.exec(
            select(func.count(CidadeRodonaves.id))
            .where(CidadeRodonaves.distancia_km == 0)
        ).first()

        null_distances = self.session.exec(
            select(func.count(CidadeRodonaves.id))
            .where(CidadeRodonaves.distancia_km.is_(None))
        ).first()

        self.report['cities_with_valid_distances'] = valid_distances
        self.report['cities_with_zero_distances'] = zero_distances
        self.report['cities_with_null_distances'] = null_distances

        print(f"   Total cities: {self.report['total_cities']}")
        print(f"   Valid distances (> 0): {valid_distances}")
        print(f"   Zero distances (filial cities): {zero_distances}")
        print(f"   Null distances (missing data): {null_distances}")

        # Calculate coverage percentage
        coverage = ((valid_distances + zero_distances) / self.report['total_cities']) * 100 if self.report['total_cities'] > 0 else 0
        self.report['distance_coverage_percent'] = round(coverage, 2)
        print(f"   Distance coverage: {coverage:.2f}%")

    def _verify_major_capitals(self):
        """Verify distance data for major Brazilian capitals"""
        print("🏛️  Verifying major capitals...")

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
                # Get state
                state = self.session.exec(
                    select(Estado).where(Estado.sigla == state_abbr)
                ).first()

                if not state:
                    self.report['major_capitals_verification'][f"{city_name}/{state_abbr}"] = {
                        'status': 'ERROR',
                        'message': f'State {state_abbr} not found'
                    }
                    continue

                # Get city
                city = self.session.exec(
                    select(CidadeRodonaves)
                    .where(CidadeRodonaves.nome == city_name)
                    .where(CidadeRodonaves.estado_id == state.id)
                ).first()

                if not city:
                    self.report['major_capitals_verification'][f"{city_name}/{state_abbr}"] = {
                        'status': 'ERROR',
                        'message': f'City {city_name} not found in {state_abbr}'
                    }
                    continue

                # Get filial info
                filial = self.session.exec(
                    select(FilialRodonaves).where(FilialRodonaves.id == city.filial_atendimento_id)
                ).first()

                verification_data = {
                    'status': 'OK',
                    'distance_km': city.distancia_km,
                    'category': city.categoria_tarifa,
                    'filial': f"{filial.nome} ({filial.codigo})" if filial else "Unknown",
                    'delivery_days': city.prazo_entrega_dias
                }

                # Validate distance makes sense for capital
                if city.distancia_km is None:
                    verification_data['status'] = 'WARNING'
                    verification_data['message'] = 'Distance is null'
                elif city.distancia_km == 0:
                    verification_data['status'] = 'INFO'
                    verification_data['message'] = 'Distance is zero (likely filial city)'
                elif city.distancia_km > 3000:  # Suspicious if > 3000km within Brazil
                    verification_data['status'] = 'WARNING'
                    verification_data['message'] = f'Distance seems too high: {city.distancia_km}km'

                self.report['major_capitals_verification'][f"{city_name}/{state_abbr}"] = verification_data

                print(f"   {city_name}/{state_abbr}: {city.distancia_km}km - {verification_data['status']}")

            except Exception as e:
                self.report['major_capitals_verification'][f"{city_name}/{state_abbr}"] = {
                    'status': 'ERROR',
                    'message': str(e)
                }

    def _sample_state_cities(self):
        """Check sample cities from each state"""
        print("🗺️  Sampling cities from each state...")

        states = self.session.exec(select(Estado)).all()

        for state in states:
            try:
                # Get sample of cities from this state (max 5)
                cities = self.session.exec(
                    select(CidadeRodonaves)
                    .where(CidadeRodonaves.estado_id == state.id)
                    .limit(5)
                ).all()

                state_data = {
                    'state_name': state.nome,
                    'total_cities': self.session.exec(
                        select(func.count(CidadeRodonaves.id))
                        .where(CidadeRodonaves.estado_id == state.id)
                    ).first(),
                    'sample_cities': [],
                    'avg_distance': 0,
                    'distance_stats': {
                        'valid': 0,
                        'zero': 0,
                        'null': 0
                    }
                }

                total_distance = 0
                valid_count = 0

                for city in cities:
                    filial = self.session.exec(
                        select(FilialRodonaves).where(FilialRodonaves.id == city.filial_atendimento_id)
                    ).first()

                    city_info = {
                        'name': city.nome,
                        'distance_km': city.distancia_km,
                        'category': city.categoria_tarifa,
                        'filial': f"{filial.codigo}" if filial else "Unknown"
                    }

                    # Track statistics
                    if city.distancia_km is None:
                        state_data['distance_stats']['null'] += 1
                    elif city.distancia_km == 0:
                        state_data['distance_stats']['zero'] += 1
                    else:
                        state_data['distance_stats']['valid'] += 1
                        total_distance += city.distancia_km
                        valid_count += 1

                    state_data['sample_cities'].append(city_info)

                # Calculate average distance for valid distances
                if valid_count > 0:
                    state_data['avg_distance'] = round(total_distance / valid_count, 2)

                # Get full state statistics
                full_stats = self.session.exec(
                    select(
                        func.count(CidadeRodonaves.id).label('total'),
                        func.count(CidadeRodonaves.distancia_km).filter(CidadeRodonaves.distancia_km > 0).label('valid'),
                        func.count(CidadeRodonaves.distancia_km).filter(CidadeRodonaves.distancia_km == 0).label('zero'),
                        func.count(CidadeRodonaves.id).filter(CidadeRodonaves.distancia_km.is_(None)).label('null')
                    )
                    .where(CidadeRodonaves.estado_id == state.id)
                ).first()

                state_data['full_stats'] = {
                    'total': full_stats.total,
                    'valid': full_stats.valid,
                    'zero': full_stats.zero,
                    'null': full_stats.null,
                    'coverage_percent': round(((full_stats.valid + full_stats.zero) / full_stats.total) * 100, 2) if full_stats.total > 0 else 0
                }

                self.report['state_sample_verification'][state.sigla] = state_data

                print(f"   {state.sigla}: {full_stats.total} cities, {state_data['full_stats']['coverage_percent']}% coverage")

            except Exception as e:
                self.report['state_sample_verification'][state.sigla] = {
                    'error': str(e)
                }

    def _check_distance_consistency(self):
        """Check consistency between nearby cities"""
        print("🧭 Checking distance consistency...")

        # Find cities within same state and compare distances
        states = self.session.exec(select(Estado).limit(5)).all()  # Check first 5 states for performance

        for state in states:
            try:
                cities = self.session.exec(
                    select(CidadeRodonaves)
                    .where(CidadeRodonaves.estado_id == state.id)
                    .where(CidadeRodonaves.distancia_km > 0)
                    .limit(10)
                ).all()

                if len(cities) < 2:
                    continue

                # Check if distances are reasonable within the state
                distances = [city.distancia_km for city in cities if city.distancia_km]
                if distances:
                    min_dist = min(distances)
                    max_dist = max(distances)
                    avg_dist = sum(distances) / len(distances)

                    consistency_data = {
                        'min_distance': min_dist,
                        'max_distance': max_dist,
                        'avg_distance': round(avg_dist, 2),
                        'sample_size': len(distances),
                        'range': max_dist - min_dist
                    }

                    # Flag potential issues
                    issues = []
                    if max_dist - min_dist > 2000:  # Very large range within state
                        issues.append(f"Large distance range: {max_dist - min_dist:.0f}km")
                    if max_dist > 3000:  # Suspicious maximum
                        issues.append(f"Very high maximum distance: {max_dist:.0f}km")

                    consistency_data['potential_issues'] = issues

                    self.report['distance_consistency_check'][state.sigla] = consistency_data

                    status = "⚠️" if issues else "✅"
                    print(f"   {state.sigla}: {min_dist:.0f}-{max_dist:.0f}km (avg: {avg_dist:.0f}km) {status}")

            except Exception as e:
                self.report['distance_consistency_check'][state.sigla] = {'error': str(e)}

    def _verify_filial_distances(self):
        """Verify that filial cities have distance = 0"""
        print("🏢 Verifying filial distances...")

        filiais = self.session.exec(select(FilialRodonaves)).all()

        for filial in filiais:
            try:
                # Find city with same name as filial in same state
                filial_city = self.session.exec(
                    select(CidadeRodonaves)
                    .where(CidadeRodonaves.nome == filial.cidade)
                    .where(CidadeRodonaves.estado_id == filial.estado_id)
                ).first()

                if filial_city:
                    verification_data = {
                        'filial_code': filial.codigo,
                        'filial_name': filial.nome,
                        'city_name': filial_city.nome,
                        'distance': filial_city.distancia_km,
                        'status': 'OK' if filial_city.distancia_km == 0 else 'WARNING',
                        'served_by_self': filial_city.filial_atendimento_id == filial.id
                    }

                    if filial_city.distancia_km != 0:
                        verification_data['message'] = f"Filial city has non-zero distance: {filial_city.distancia_km}km"
                        self.report['anomalies'].append(
                            f"Filial {filial.codigo} city has distance {filial_city.distancia_km}km instead of 0"
                        )

                    self.report['filial_distance_verification'][filial.codigo] = verification_data

                    status = "✅" if verification_data['status'] == 'OK' else "⚠️"
                    print(f"   {filial.codigo} ({filial.cidade}): {filial_city.distancia_km}km {status}")
                else:
                    self.report['filial_distance_verification'][filial.codigo] = {
                        'status': 'NOT_FOUND',
                        'message': f'City {filial.cidade} not found for filial {filial.codigo}'
                    }

            except Exception as e:
                self.report['filial_distance_verification'][filial.codigo] = {
                    'status': 'ERROR',
                    'message': str(e)
                }

    def _analyze_anomalies(self):
        """Find and report distance anomalies"""
        print("🔍 Analyzing distance anomalies...")

        try:
            # Cities with very high distances (>2500km)
            high_distance_cities = self.session.exec(
                select(CidadeRodonaves, Estado.sigla)
                .join(Estado)
                .where(CidadeRodonaves.distancia_km > 2500)
            ).all()

            for city, state_sigla in high_distance_cities:
                self.report['anomalies'].append(
                    f"Very high distance: {city.nome}/{state_sigla} = {city.distancia_km}km"
                )

            # Cities with negative distances
            negative_distance_cities = self.session.exec(
                select(CidadeRodonaves, Estado.sigla)
                .join(Estado)
                .where(CidadeRodonaves.distancia_km < 0)
            ).all()

            for city, state_sigla in negative_distance_cities:
                self.report['anomalies'].append(
                    f"Negative distance: {city.nome}/{state_sigla} = {city.distancia_km}km"
                )

            # States with very low coverage
            states_low_coverage = []
            for state_code, data in self.report['state_sample_verification'].items():
                if 'full_stats' in data and data['full_stats']['coverage_percent'] < 50:
                    states_low_coverage.append(f"{state_code}: {data['full_stats']['coverage_percent']}%")

            if states_low_coverage:
                self.report['anomalies'].append(
                    f"States with low distance coverage: {', '.join(states_low_coverage)}"
                )

            print(f"   Found {len(self.report['anomalies'])} anomalies")

        except Exception as e:
            self.report['anomalies'].append(f"Error analyzing anomalies: {str(e)}")

    def print_summary_report(self):
        """Print a formatted summary of the verification results"""
        print("\n" + "="*80)
        print("📋 DISTANCE VERIFICATION SUMMARY REPORT")
        print("="*80)

        # Basic statistics
        print(f"\n📊 DATABASE OVERVIEW:")
        print(f"   Total States: {self.report['total_states']}")
        print(f"   Total Cities: {self.report['total_cities']}")
        print(f"   Distance Coverage: {self.report.get('distance_coverage_percent', 0)}%")
        print(f"   Cities with valid distances: {self.report['cities_with_valid_distances']}")
        print(f"   Cities with zero distances (filial): {self.report['cities_with_zero_distances']}")
        print(f"   Cities with null distances (missing): {self.report['cities_with_null_distances']}")

        # Major capitals status
        print(f"\n🏛️  MAJOR CAPITALS STATUS:")
        for capital, data in self.report['major_capitals_verification'].items():
            status_icon = "✅" if data['status'] == 'OK' else "⚠️" if data['status'] == 'WARNING' else "❌"
            distance = f"{data.get('distance_km', 'N/A')}km" if data.get('distance_km') is not None else "No distance"
            print(f"   {status_icon} {capital}: {distance}")
            if 'message' in data:
                print(f"      {data['message']}")

        # State coverage summary
        print(f"\n🗺️  STATE COVERAGE SUMMARY:")
        for state_code, data in self.report['state_sample_verification'].items():
            if 'full_stats' in data:
                coverage = data['full_stats']['coverage_percent']
                status_icon = "✅" if coverage >= 90 else "⚠️" if coverage >= 70 else "❌"
                print(f"   {status_icon} {state_code}: {data['full_stats']['total']} cities, {coverage}% coverage")

        # Filial verification
        print(f"\n🏢 FILIAL DISTANCE VERIFICATION:")
        ok_count = sum(1 for data in self.report['filial_distance_verification'].values() if data.get('status') == 'OK')
        total_filiais = len(self.report['filial_distance_verification'])
        print(f"   {ok_count}/{total_filiais} filials have correct zero distance")

        # Anomalies
        print(f"\n⚠️  ANOMALIES DETECTED:")
        if self.report['anomalies']:
            for anomaly in self.report['anomalies'][:10]:  # Show first 10
                print(f"   • {anomaly}")
            if len(self.report['anomalies']) > 10:
                print(f"   ... and {len(self.report['anomalies']) - 10} more")
        else:
            print("   ✅ No major anomalies detected")

        # Final assessment
        print(f"\n🎯 FINAL ASSESSMENT:")
        coverage = self.report.get('distance_coverage_percent', 0)
        if coverage >= 95:
            print("   ✅ EXCELLENT: Distance data is comprehensive and well-imported")
        elif coverage >= 85:
            print("   ✅ GOOD: Distance data coverage is adequate with minor gaps")
        elif coverage >= 70:
            print("   ⚠️  FAIR: Distance data has significant gaps that should be addressed")
        else:
            print("   ❌ POOR: Distance data coverage is insufficient")

        print("\n" + "="*80)


def main():
    """Main execution function"""
    print("Rodonaves Distance Verification Tool")
    print("=" * 50)

    try:
        verifier = DistanceVerificationReport()
        report = verifier.run_verification()
        verifier.print_summary_report()

        # Save detailed report to file
        import json
        with open('distance_verification_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)

        print(f"\n💾 Detailed report saved to: distance_verification_report.json")

    except Exception as e:
        print(f"❌ Failed to run verification: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())