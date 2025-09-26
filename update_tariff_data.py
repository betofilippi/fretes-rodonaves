#!/usr/bin/env python3
"""
Comprehensive Tariff Data Update Script
Imports real Rodonaves tariff data from PDF and updates database
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from sqlmodel import Session, select
from frete_app.db import engine, create_db_and_tables
from frete_app.models import VersaoTabela, ParametrosGerais
from frete_app.models_extended import (
    TabelaTarifaCompleta, HistoricoImportacao, CidadeRodonaves, Estado
)
from pdf_tariff_parser import PDFTariffParser
from state_config import StateConfigManager


class TariffDataUpdater:
    """
    Comprehensive script to update all tariff data from official Rodonaves PDF
    """

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.parser = PDFTariffParser()
        self.config_manager = StateConfigManager()
        self.stats = {
            'categories_updated': 0,
            'categories_created': 0,
            'states_processed': 0,
            'validation_errors': 0,
            'warnings': []
        }

    def execute_full_update(self, session: Session) -> Dict[str, Any]:
        """
        Main execution method that orchestrates the complete update
        """
        try:
            print("Starting comprehensive tariff data update...")

            # Step 1: Parse PDF data
            print("Step 1: Parsing PDF tariff data...")
            parsed_data = self.parser.parse_pdf(self.pdf_path)
            if not parsed_data['states']:
                raise Exception("No tariff data extracted from PDF")

            print(f"  - Extracted data for {len(parsed_data['states'])} states")
            print(f"  - Found {parsed_data['import_info']['categories_found']} categories")

            # Step 2: Create new version record
            print("Step 2: Creating new version record...")
            version = self.create_new_version(session)
            print(f"  - Created version ID: {version.id}")

            # Step 3: Update tariff tables with real data
            print("Step 3: Updating tariff tables...")
            self.update_tariff_tables(session, parsed_data, version.id)

            # Step 4: Update general parameters
            print("Step 4: Updating general parameters...")
            self.update_general_parameters(session, parsed_data, version.id)

            # Step 5: Create audit trail
            print("Step 5: Creating audit trail...")
            self.create_audit_trail(session, version.id, parsed_data)

            # Step 6: Validate results
            print("Step 6: Validating results...")
            validation_result = self.validate_update_results(session, version.id)

            result = {
                'version_id': version.id,
                'stats': self.stats,
                'validation': validation_result,
                'success': True
            }

            print(f"\nUpdate completed successfully!")
            self.print_update_summary(result)

            return result

        except Exception as e:
            error_msg = f"Critical error during tariff update: {str(e)}"
            print(f"ERROR: {error_msg}")
            self.stats['warnings'].append(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'stats': self.stats
            }

    def create_new_version(self, session: Session) -> VersaoTabela:
        """Create new version record for this tariff update"""
        version = VersaoTabela(
            nome=f"PDF Import {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            descricao=f"Real tariff data imported from {Path(self.pdf_path).name}",
            ativa=True,
            data_importacao=datetime.now()
        )

        # Deactivate previous versions
        previous_versions = session.exec(
            select(VersaoTabela).where(VersaoTabela.ativa == True)
        ).all()
        for prev_version in previous_versions:
            prev_version.ativa = False

        session.add(version)
        session.commit()
        session.refresh(version)

        return version

    def update_tariff_tables(self, session: Session, parsed_data: Dict, version_id: int):
        """Update TabelaTarifaCompleta with real PDF data"""

        for state_code, state_data in parsed_data['states'].items():
            print(f"  Processing {state_code}...")

            for category, weight_data in state_data['categories'].items():
                categoria_completa = f"{state_code}_{category}"

                # Check if record exists
                existing = session.exec(
                    select(TabelaTarifaCompleta).where(
                        TabelaTarifaCompleta.versao_id == version_id,
                        TabelaTarifaCompleta.categoria_completa == categoria_completa
                    )
                ).first()

                if existing:
                    # Update existing record
                    self.update_tariff_record(existing, weight_data, state_data)
                    self.stats['categories_updated'] += 1
                else:
                    # Create new record
                    new_record = self.create_tariff_record(
                        version_id, state_code, category, weight_data, state_data
                    )
                    session.add(new_record)
                    self.stats['categories_created'] += 1

            self.stats['states_processed'] += 1

        session.commit()
        print(f"  - Updated/created {self.stats['categories_updated'] + self.stats['categories_created']} tariff records")

    def create_tariff_record(self, version_id: int, state_code: str, category: str,
                           weight_data: Dict, state_data: Dict) -> TabelaTarifaCompleta:
        """Create new tariff record with real PDF data"""

        # Get state parameters
        state_params = self.config_manager.get_state_parameters(state_code)

        return TabelaTarifaCompleta(
            versao_id=version_id,
            estado_sigla=state_code,
            categoria=category,
            categoria_completa=f"{state_code}_{category}",

            # Real weight range data from PDF
            ate_10=weight_data.get('ate_10', 0.0),
            ate_20=weight_data.get('ate_20', 0.0),
            ate_40=weight_data.get('ate_40', 0.0),
            ate_60=weight_data.get('ate_60', 0.0),
            ate_100=weight_data.get('ate_100', 0.0),
            excedente_por_kg=weight_data.get('excedente_por_kg', 0.0),

            # State-specific parameters
            gris_percent_especial=state_params.get('gris_percent'),
            fvalor_percent_especial=state_params.get('fvalor_percent'),
            icms_percent=state_params.get('icms_percent'),
            pedagio_adicional=state_params.get('pedagio_special'),

            # Metadata
            importado_pdf=Path(self.pdf_path).name,
            data_atualizacao=datetime.now()
        )

    def update_tariff_record(self, record: TabelaTarifaCompleta,
                           weight_data: Dict, state_data: Dict):
        """Update existing tariff record with real PDF data"""

        # Update weight ranges
        record.ate_10 = weight_data.get('ate_10', record.ate_10)
        record.ate_20 = weight_data.get('ate_20', record.ate_20)
        record.ate_40 = weight_data.get('ate_40', record.ate_40)
        record.ate_60 = weight_data.get('ate_60', record.ate_60)
        record.ate_100 = weight_data.get('ate_100', record.ate_100)
        record.excedente_por_kg = weight_data.get('excedente_por_kg', record.excedente_por_kg)

        # Update state parameters
        state_params = self.config_manager.get_state_parameters(record.estado_sigla)
        record.gris_percent_especial = state_params.get('gris_percent')
        record.fvalor_percent_especial = state_params.get('fvalor_percent')
        record.pedagio_adicional = state_params.get('pedagio_special')

        # Update metadata
        record.importado_pdf = Path(self.pdf_path).name
        record.data_atualizacao = datetime.now()

    def update_general_parameters(self, session: Session, parsed_data: Dict, version_id: int):
        """Update general parameters with regional variations"""

        general_params = parsed_data.get('general_params', {})

        # Create or update general parameters
        existing_params = session.exec(
            select(ParametrosGerais).where(
                ParametrosGerais.versao_id == version_id
            )
        ).first()

        if existing_params:
            # Update existing
            self.update_params_record(existing_params, general_params)
        else:
            # Create new
            new_params = self.create_params_record(version_id, general_params)
            session.add(new_params)

        session.commit()

    def create_params_record(self, version_id: int, general_params: Dict) -> ParametrosGerais:
        """Create new general parameters record"""
        return ParametrosGerais(
            versao_id=version_id,
            cubagem_kg_por_m3=general_params.get('cubagem_kg_por_m3', 200.0),
            fvalor_percent_padrao=0.00316,  # Standard rate for most regions
            fvalor_min=4.37,
            gris_percent_ate_10k=0.001,
            gris_percent_acima_10k=0.0023,
            gris_min=1.10,
            pedagio_por_100kg=general_params.get('pedagio_fixo', 6.46),
            icms_percent=0.12,
            importado_em=datetime.now()
        )

    def update_params_record(self, record: ParametrosGerais, general_params: Dict):
        """Update existing general parameters record"""
        record.cubagem_kg_por_m3 = general_params.get('cubagem_kg_por_m3', record.cubagem_kg_por_m3)
        record.pedagio_por_100kg = general_params.get('pedagio_fixo', record.pedagio_por_100kg)
        record.importado_em = datetime.now()

    def create_audit_trail(self, session: Session, version_id: int, parsed_data: Dict):
        """Create comprehensive audit trail"""

        historico = HistoricoImportacao(
            tipo_arquivo="PDF_TARIFF_COMPLETE",
            nome_arquivo=Path(self.pdf_path).name,
            total_registros=parsed_data['import_info']['categories_found'],
            registros_importados=self.stats['categories_created'],
            registros_atualizados=self.stats['categories_updated'],
            registros_erro=self.stats['validation_errors'],
            status="SUCESSO" if self.stats['validation_errors'] == 0 else "PARCIAL",
            mensagem_erro="; ".join(self.stats['warnings'][:5]) if self.stats['warnings'] else None,
            detalhes_importacao=f"States: {self.stats['states_processed']}, "
                               f"PDF pages: {parsed_data['import_info']['pages_processed']}, "
                               f"Version: {version_id}"
        )

        session.add(historico)
        session.commit()

    def validate_update_results(self, session: Session, version_id: int) -> Dict[str, Any]:
        """Validate the updated tariff data for completeness and consistency"""

        validation_result = {
            'total_records': 0,
            'valid_progressions': 0,
            'invalid_progressions': [],
            'missing_states': [],
            'coverage_by_region': {},
            'errors': []
        }

        try:
            # Count total records
            total_records = session.exec(
                select(TabelaTarifaCompleta).where(
                    TabelaTarifaCompleta.versao_id == version_id
                )
            ).all()

            validation_result['total_records'] = len(total_records)

            # Validate weight progressions
            for record in total_records:
                if self.validate_weight_progression(record):
                    validation_result['valid_progressions'] += 1
                else:
                    validation_result['invalid_progressions'].append(
                        f"{record.categoria_completa}"
                    )

            # Check state coverage
            expected_states = set(self.config_manager.get_all_state_categories().keys())
            found_states = set(record.estado_sigla for record in total_records)
            validation_result['missing_states'] = list(expected_states - found_states)

            # Coverage by region
            regional_coverage = {}
            for record in total_records:
                region = self.config_manager.state_regional_config[record.estado_sigla]['region']
                if region not in regional_coverage:
                    regional_coverage[region] = []
                regional_coverage[region].append(record.estado_sigla)

            validation_result['coverage_by_region'] = {
                region: list(set(states)) for region, states in regional_coverage.items()
            }

        except Exception as e:
            validation_result['errors'].append(f"Validation error: {str(e)}")

        return validation_result

    def validate_weight_progression(self, record: TabelaTarifaCompleta) -> bool:
        """Validate that weight ranges are in ascending order"""
        try:
            weights = [
                record.ate_10 or 0,
                record.ate_20 or 0,
                record.ate_40 or 0,
                record.ate_60 or 0,
                record.ate_100 or 0
            ]

            # Allow some tolerance for equal values but ensure no decreases
            for i in range(len(weights) - 1):
                if weights[i] > weights[i + 1] and weights[i + 1] > 0:
                    return False

            return True
        except:
            return False

    def print_update_summary(self, result: Dict):
        """Print comprehensive update summary"""
        print(f"\n" + "="*60)
        print(f"TARIFF UPDATE SUMMARY")
        print(f"="*60)
        print(f"Version ID: {result['version_id']}")
        print(f"States processed: {self.stats['states_processed']}")
        print(f"Categories created: {self.stats['categories_created']}")
        print(f"Categories updated: {self.stats['categories_updated']}")
        print(f"Total tariff records: {result['validation']['total_records']}")

        if result['validation']['invalid_progressions']:
            print(f"\nWARNINGS:")
            print(f"  Invalid weight progressions: {len(result['validation']['invalid_progressions'])}")
            for invalid in result['validation']['invalid_progressions'][:5]:
                print(f"    - {invalid}")

        if result['validation']['missing_states']:
            print(f"  Missing states: {result['validation']['missing_states']}")

        print(f"\nCoverage by region:")
        for region, states in result['validation']['coverage_by_region'].items():
            print(f"  {region}: {len(states)} states - {states}")

        print(f"\n" + "="*60)


def main():
    """Main execution function"""

    # Configuration
    PDF_PATH = r"C:\Users\Beto\Dropbox\NXT\Dev\fretes-rodonaves\432968 MONTERREY 2025 (1) (1).pdf"

    if not Path(PDF_PATH).exists():
        print(f"ERROR: PDF file not found: {PDF_PATH}")
        return 1

    try:
        # Initialize database
        print("Initializing database...")
        create_db_and_tables()

        with Session(engine) as session:
            # Create updater instance
            updater = TariffDataUpdater(PDF_PATH)

            # Execute full update
            result = updater.execute_full_update(session)

            if result['success']:
                print("SUCCESS: Tariff data updated successfully!")

                # Show sample of updated data
                print(f"\nSample updated records:")
                sample_records = session.exec(
                    select(TabelaTarifaCompleta).where(
                        TabelaTarifaCompleta.versao_id == result['version_id']
                    ).limit(5)
                ).all()

                for record in sample_records:
                    print(f"  {record.categoria_completa}: "
                          f"R$ {record.ate_10:.2f} - {record.ate_20:.2f} - "
                          f"{record.ate_40:.2f} - {record.ate_60:.2f} - "
                          f"{record.ate_100:.2f} (exc: {record.excedente_por_kg:.3f})")

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