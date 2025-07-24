<?php

declare(strict_types=1);

namespace Infoclimat\Cron\DonneesPubliques\Radar;

require_once __DIR__ . '/conversion.php';

use function Infoclimat\Radar\Conversion\real_execute_download_conversion_and_generate_accumulations;

function execute(): void
{
    real_execute_download_conversion_and_generate_accumulations();
}

execute();
