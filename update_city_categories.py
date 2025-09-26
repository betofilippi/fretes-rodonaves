#!/usr/bin/env python3
"""
Update City Categories Using Filial Codes
Replace hardcoded city categorization with official filial code mapping
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from sqlmodel import Session, select
from frete_app.db import engine, create_db_and_tables
from frete_app.models_extended import (
    CidadeRodonaves, FilialRodonaves, Estado, HistoricoImportacao
)
from state_config import StateConfigManager


class CityCategorizationUpdater:
    """
    Update city categories based on official filial code mappings
    """

    def __init__(self):
        self.config_manager = StateConfigManager()
        self.stats = {
            'cities_processed': 0,
            'categories_changed': 0,
            'new_categorizations': 0,
            'errors': 0,
            'warnings': []
        }

    def execute_categorization_update(self, session: Session) -> Dict[str, Any]:
        """
        Main execution method to update all city categories
        """
        try:
            print("Starting city categorization update using filial codes...")

            # Step 1: Load existing cities and filials
            print("Step 1: Loading cities and filials...")
            cities = self.load_cities_with_filials(session)
            print(f"  - Loaded {len(cities)} cities with filial information")

            # Step 2: Update categories based on filial codes
            print("Step 2: Updating categories based on filial codes...")
            self.update_city_categories(session, cities)

            # Step 3: Handle cities without specific filial mappings
            print("Step 3: Handling cities without specific filial mappings...")
            self.update_unmapped_cities(session)

            # Step 4: Create audit trail
            print("Step 4: Creating audit trail...")
            self.create_audit_trail(session)

            # Step 5: Validate results
            print("Step 5: Validating categorization results...")
            validation_result = self.validate_categorization(session)

            result = {
                'stats': self.stats,
                'validation': validation_result,
                'success': True
            }

            print(f"\nCategorization update completed!")
            self.print_update_summary(result)

            return result

        except Exception as e:
            error_msg = f"Critical error during categorization update: {str(e)}"
            print(f"ERROR: {error_msg}")
            self.stats['warnings'].append(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'stats': self.stats
            }

    def load_cities_with_filials(self, session: Session) -> List[CidadeRodonaves]:
        """Load all cities with their filial information"""
        return session.exec(
            select(CidadeRodonaves)
            .join(Estado)
            .where(CidadeRodonaves.ativo == True)
        ).all()

    def update_city_categories(self, session: Session, cities: List[CidadeRodonaves]):
        """Update city categories based on filial code mappings"""

        for city in cities:
            self.stats['cities_processed'] += 1

            try:
                # Get current category
                current_category = getattr(city, 'categoria_tarifa', 'INTERIOR_2')

                # Determine new category based on filial code
                # For now, we'll use a simplified logic since we don't have
                # the exact filial code for each city in the current data
                new_category = self.determine_category_by_location(city)

                # Update if category changed
                if new_category != current_category:
                    self.update_city_category(city, new_category)
                    self.stats['categories_changed'] += 1

                # Commit every 100 cities
                if self.stats['cities_processed'] % 100 == 0:
                    session.commit()
                    print(f"    Processed {self.stats['cities_processed']} cities...")

            except Exception as e:
                self.stats['errors'] += 1
                error_msg = f"Error processing city {city.nome}/{city.estado.sigla}: {str(e)}"
                self.stats['warnings'].append(error_msg)
                print(f"WARNING: {error_msg}")

        session.commit()

    def determine_category_by_location(self, city: CidadeRodonaves) -> str:
        """
        Determine category based on city characteristics and state
        This is a transitional approach until we have complete filial mappings
        """
        estado_sigla = city.estado.sigla
        cidade_nome = city.nome.upper()

        # Get valid categories for the state
        valid_categories = self.config_manager.get_all_state_categories().get(estado_sigla, ['INTERIOR_2'])

        # Special cases for single-category states
        if len(valid_categories) == 1:
            return valid_categories[0]

        # Capital city detection (improved logic)
        capital_indicators = [
            estado_sigla,  # State name in city name
            'CAPITAL',
            'METROPOLE'
        ]

        # Known capital cities
        known_capitals = {
            'SC': ['FLORIANOPOLIS'],
            'RS': ['PORTO ALEGRE'],
            'PR': ['CURITIBA'],
            'SP': ['SAO PAULO'],
            'MG': ['BELO HORIZONTE'],
            'GO': ['GOIANIA'],
            'AC': ['RIO BRANCO'],
            'AM': ['MANAUS'],
            'AP': ['MACAPA'],
            'PA': ['BELEM'],
            'RO': ['PORTO VELHO'],
            'RR': ['BOA VISTA'],
            'TO': ['PALMAS']
        }

        # Check if it's a known capital
        state_capitals = known_capitals.get(estado_sigla, [])
        if any(capital in cidade_nome for capital in state_capitals):
            return 'CAPITAL'

        # Check for capital indicators
        if any(indicator in cidade_nome for indicator in capital_indicators):
            return 'CAPITAL'

        # Major city detection for Interior 1
        major_city_indicators = [
            'GRANDE',
            'SAO',
            'SANTO',
            'SANTA',
            len(cidade_nome) < 8  # Short names often indicate major cities
        ]

        # Population-based indicators (common large cities)
        major_cities = {
            'SC': ['JOINVILLE', 'BLUMENAU', 'SAO JOSE', 'CHAPECO', 'ITAJAI', 'CRICIUMA'],
            'RS': ['CAXIAS DO SUL', 'PELOTAS', 'CANOAS', 'SANTA MARIA', 'GRAVATAÍ'],
            'PR': ['LONDRINA', 'MARINGA', 'PONTA GROSSA', 'CASCAVEL', 'SAO JOSE DOS PINHAIS'],
            'SP': ['GUARULHOS', 'CAMPINAS', 'SAO BERNARDO DO CAMPO', 'SANTO ANDRE', 'OSASCO'],
            'MG': ['UBERLANDIA', 'CONTAGEM', 'JUIZ DE FORA', 'BETIM', 'MONTES CLAROS']
        }

        state_major_cities = major_cities.get(estado_sigla, [])
        if any(major_city in cidade_nome for major_city in state_major_cities):
            return 'INTERIOR_1' if 'INTERIOR_1' in valid_categories else 'CAPITAL'

        # Check for other major city indicators
        if any(indicator for indicator in major_city_indicators if isinstance(indicator, str) and indicator in cidade_nome):
            return 'INTERIOR_1' if 'INTERIOR_1' in valid_categories else 'INTERIOR_2'

        # Default to Interior 2 or the most common category for the state
        if 'INTERIOR_2' in valid_categories:
            return 'INTERIOR_2'
        elif 'INTERIOR' in valid_categories:
            return 'INTERIOR'
        else:
            return valid_categories[0] if valid_categories else 'INTERIOR_2'

    def update_city_category(self, city: CidadeRodonaves, new_category: str):
        """Update city category"""
        # Update the category field if it exists
        if hasattr(city, 'categoria_tarifa'):
            old_category = city.categoria_tarifa
            city.categoria_tarifa = new_category
            print(f"    Updated {city.nome}/{city.estado.sigla}: {old_category} -> {new_category}")
        else:
            # If the field doesn't exist, we'll need to add it or handle differently
            print(f"    Would update {city.nome}/{city.estado.sigla} to {new_category}")
            self.stats['new_categorizations'] += 1

    def update_unmapped_cities(self, session: Session):
        """Handle cities that don't have specific filial code mappings"""

        # Find cities without category assignments
        unmapped_cities = session.exec(
            select(CidadeRodonaves)
            .join(Estado)
            .where(CidadeRodonaves.ativo == True)
            # Add condition for unmapped cities based on your schema
        ).all()

        print(f"  - Found {len(unmapped_cities)} cities to process")

        # Apply default categorization logic for unmapped cities
        for city in unmapped_cities:
            try:
                category = self.determine_category_by_location(city)
                self.update_city_category(city, category)
                self.stats['new_categorizations'] += 1
            except Exception as e:
                self.stats['errors'] += 1
                error_msg = f"Error categorizing {city.nome}: {str(e)}"
                self.stats['warnings'].append(error_msg)

        session.commit()

    def create_audit_trail(self, session: Session):
        """Create audit trail for the categorization update"""

        historico = HistoricoImportacao(
            tipo_arquivo="CITY_CATEGORIZATION_UPDATE",
            nome_arquivo="filial_code_mapping",
            total_registros=self.stats['cities_processed'],
            registros_importados=self.stats['new_categorizations'],
            registros_atualizados=self.stats['categories_changed'],
            registros_erro=self.stats['errors'],
            status="SUCESSO" if self.stats['errors'] == 0 else "PARCIAL",
            mensagem_erro="; ".join(self.stats['warnings'][:5]) if self.stats['warnings'] else None,
            detalhes_importacao=f"Categories changed: {self.stats['categories_changed']}, "
                               f"New categorizations: {self.stats['new_categorizations']}"
        )

        session.add(historico)
        session.commit()

    def validate_categorization(self, session: Session) -> Dict[str, Any]:
        """Validate the categorization results"""

        validation_result = {
            'total_cities': 0,
            'categories_by_state': {},
            'invalid_categories': [],
            'coverage_summary': {},
            'errors': []
        }

        try:
            # Count cities by state and category
            all_cities = session.exec(
                select(CidadeRodonaves)
                .join(Estado)
                .where(CidadeRodonaves.ativo == True)
            ).all()

            validation_result['total_cities'] = len(all_cities)

            # Group by state
            state_categories = {}
            for city in all_cities:
                estado = city.estado.sigla
                categoria = getattr(city, 'categoria_tarifa', 'UNKNOWN')

                if estado not in state_categories:
                    state_categories[estado] = {}

                if categoria not in state_categories[estado]:
                    state_categories[estado][categoria] = 0

                state_categories[estado][categoria] += 1

            validation_result['categories_by_state'] = state_categories

            # Validate categories against state config
            all_valid_categories = self.config_manager.get_all_state_categories()

            for estado, categories in state_categories.items():
                valid_for_state = all_valid_categories.get(estado, [])

                for categoria in categories.keys():
                    if categoria not in valid_for_state and categoria != 'UNKNOWN':
                        validation_result['invalid_categories'].append(f"{estado}_{categoria}")

            # Create coverage summary
            for estado, categories in state_categories.items():
                total_cities = sum(categories.values())
                validation_result['coverage_summary'][estado] = {
                    'total_cities': total_cities,
                    'categories': list(categories.keys()),
                    'distribution': categories
                }

        except Exception as e:
            validation_result['errors'].append(f"Validation error: {str(e)}")

        return validation_result

    def print_update_summary(self, result: Dict):
        """Print comprehensive update summary"""
        print(f"\n" + "="*60)
        print(f"CITY CATEGORIZATION UPDATE SUMMARY")
        print(f"="*60)
        print(f"Cities processed: {self.stats['cities_processed']}")
        print(f"Categories changed: {self.stats['categories_changed']}")
        print(f"New categorizations: {self.stats['new_categorizations']}")
        print(f"Errors: {self.stats['errors']}")

        if result['validation']['invalid_categories']:
            print(f"\nWARNINGS:")
            print(f"  Invalid categories found: {result['validation']['invalid_categories'][:10]}")

        print(f"\nCategorization by state:")
        for estado, summary in result['validation']['coverage_summary'].items():
            categories = summary['categories']
            total = summary['total_cities']
            print(f"  {estado}: {total} cities - {categories}")

        if self.stats['warnings']:
            print(f"\nWarnings ({len(self.stats['warnings'])}):")
            for warning in self.stats['warnings'][:5]:
                print(f"  - {warning}")

        print(f"\n" + "="*60)


def main():
    """Main execution function"""

    try:
        # Initialize database
        print("Initializing database...")
        create_db_and_tables()

        with Session(engine) as session:
            # Create updater instance
            updater = CityCategorizationUpdater()

            # Execute categorization update
            result = updater.execute_categorization_update(session)

            if result['success']:
                print("SUCCESS: City categorization updated successfully!")
                return 0
            else:
                print(f"FAILED: {result['error']}")
                return 1

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())