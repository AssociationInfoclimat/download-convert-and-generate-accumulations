<?php

declare(strict_types=1);

namespace Infoclimat\Radar\Conversion;

require_once __DIR__ . '/date.php';
require_once __DIR__ . '/io.php';
require_once __DIR__ . '/meteofrance-api.php';
require_once __DIR__ . '/radar.php';
require_once __DIR__ . '/tiles.php';

use Infoclimat\IO\CommandExecutor;
use Infoclimat\IO\FakeOutputer;
use Infoclimat\IO\FileExistanceChecker;
use Infoclimat\IO\FileMover;
use Infoclimat\IO\Outputer;
use Infoclimat\IO\RealCommandExecutor;
use Infoclimat\IO\RealFileExistanceChecker;
use Infoclimat\IO\RealFileMover;
use Infoclimat\IO\RealOutputer;
use Infoclimat\MeteoFrance\API\APIFileDownloader;
use Infoclimat\MeteoFrance\API\RealAPIFileDownloader;
use Infoclimat\Radar\FileAppender;
use Infoclimat\Radar\RealFileAppender;
use Infoclimat\Tiles\LastTilesTimestampsRepository;
use Infoclimat\Tiles\RealLastTilesTimestampsRepository;

use function Infoclimat\Date\mn;
use function Infoclimat\Radar\execute_download;
use function Infoclimat\Radar\get_file_key;
use function Infoclimat\Radar\get_tile_path;

use const Infoclimat\Radar\LAME_D_EAU;
use const Infoclimat\Radar\ZONES;

function get_tmp_ram_path(string $file_path): string
{
    $file_name = basename($file_path);
    return "/dev/shm/{$file_name}";
}

function get_h5_path(string $zone, int $timestamp): string
{
    $file_key = get_file_key(LAME_D_EAU, $zone);
    return get_tile_path($file_key, $timestamp, 'h5');
}

function get_tif_path(string $zone, int $timestamp): string
{
    $file_key = get_file_key(LAME_D_EAU, $zone);
    return get_tile_path($file_key, $timestamp, 'tif');
}

function get_radaric_key(string $zone): string
{
    return "radaric_MF_{$zone}";
}

function get_colored_tif_path(string $zone, int $timestamp): string
{
    $key = get_radaric_key($zone);
    return get_tile_path($key, $timestamp, 'tif');
}

function convert_h5_to_tif(
    string               $h5_file_path,
    string               $tif_file_path,
    bool                 $replace_existing,
    CommandExecutor      $command_executor,
    FileExistanceChecker $file_existance_checker,
    FileMover            $file_mover,
    Outputer             $outputer = new FakeOutputer()
): void {
    $hd5_tmp_ram_path = get_tmp_ram_path($h5_file_path);
    $tif_tmp_ram_path = get_tmp_ram_path($tif_file_path);
    if ($file_existance_checker->isFile($tif_file_path)) {
        if (!$replace_existing) {
            $outputer->echo(
                <<<TXT
                    Skipping :
                      - h5 {$h5_file_path}
                      - because tif {$tif_file_path}
                          already exists and replace mode is not active (--replace or --replace=true).\n
                    TXT
            );
            return;
        }
        $outputer->echo("Replacing existing tif {$tif_file_path}\n");
    }
    $outputer->echo(
        <<<TXT
            Converting :
              - h5 {$h5_file_path}
              - to tif {$tif_file_path}\n
            TXT
    );
    $create_tmp_ram_copy = <<<SH
        cp {$h5_file_path} {$hd5_tmp_ram_path} 2>&1
        SH;
    $convert_options = [
        '-t_srs EPSG:3857',
        '-tr 300 300',
        '-r lanczos',
        '-srcnodata 65535',
        "-co 'COMPRESS=LZW'",
        "-co 'PREDICTOR=YES'",
        '-of COG',
        '-overwrite',
    ];
    $convert_options = implode(' ', $convert_options);
    $convert_command = <<<SH
        gdalwarp {$convert_options} HDF5:"{$hd5_tmp_ram_path}"://dataset1/data1/data {$tif_tmp_ram_path} 2>&1
        SH;
    $outputer->echo("Running : {$create_tmp_ram_copy}\n");
    $outputer->echo($command_executor->shell_exec($create_tmp_ram_copy) ?? '');
    $outputer->echo("Running : {$convert_command}\n");
    $outputer->echo($command_executor->shell_exec($convert_command) ?? '');
    $file_mover->moveFile($tif_tmp_ram_path, $tif_file_path, null, $outputer);
}

function color_tif(
    string               $tif_file_path,
    string               $colored_file_path,
    bool                 $replace_existing,
    CommandExecutor      $command_executor,
    FileExistanceChecker $file_existance_checker,
    FileMover            $file_mover,
    Outputer             $outputer = new FakeOutputer()
): void {
    $tif_tmp_ram_path = get_tmp_ram_path($tif_file_path);
    $colored_tmp_ram_path = get_tmp_ram_path($colored_file_path);
    if ($file_existance_checker->isFile($colored_file_path)) {
        if (!$replace_existing) {
            $outputer->echo(
                <<<TXT
                    Skipping :
                      - tif {$tif_file_path}
                      - because colored tif {$colored_file_path}
                          already exists and replace mode is not active (--replace or --replace=true).\n
                    TXT
            );
            return;
        }
        $outputer->echo("Replacing existing colored tif {$colored_file_path}\n");
    }
    $outputer->echo(
        <<<TXT
            Converting :
              - tif {$tif_file_path}
              - to colored tif {$colored_file_path}\n
            TXT
    );
    $create_tmp_ram_copy = <<<SH
        cp {$tif_file_path} {$tif_tmp_ram_path} 2>&1
        SH;
    $convert_options = [
        '-alpha',
        '-nearest_color_entry',
        "-co 'COMPRESS=JPEG'",
        "-co 'PREDICTOR=YES'",
        '-of COG',
    ];
    $convert_options = implode(' ', $convert_options);
    $palette_path = dirname(__DIR__) . '/palettes/LAME_D_EAU_vers_RGBi.pal';
    $convert_command = <<<SH
        gdaldem color-relief {$tif_tmp_ram_path} {$palette_path} {$colored_tmp_ram_path} {$convert_options} 2>&1
        SH;
    $outputer->echo("Running : {$create_tmp_ram_copy}\n");
    $outputer->echo($command_executor->shell_exec($create_tmp_ram_copy) ?? '');
    $outputer->echo("Running : {$convert_command}\n");
    $outputer->echo($command_executor->shell_exec($convert_command) ?? '');
    $file_mover->moveFile($colored_tmp_ram_path, $colored_file_path, null, $outputer);
}

function compute_cumuls(
    string          $zone,
    int             $timestamp,
    CommandExecutor $command_executor,
    Outputer        $outputer = new FakeOutputer()
): void {
    $PYTHON_SCRIPT_PROJECT_PATH = dirname(__DIR__) . '/generate-radaric-mf-values-accumulations';
    $command = <<<SH
        cd {$PYTHON_SCRIPT_PROJECT_PATH} && poetry run python ./generate_radaric_mf_values_accumulations/main.py --timestamp {$timestamp} --zone {$zone} 2>&1
        SH;
    $outputer->echo("Running : {$command}\n");
    $outputer->echo($command_executor->shell_exec($command) ?? '');
}

function compute_cumuls_from_all_zones(
    int             $timestamp,
    CommandExecutor $command_executor,
    Outputer        $outputer = new FakeOutputer()
): void {
    $PYTHON_SCRIPT_PROJECT_PATH = dirname(__DIR__) . '/generate-radaric-mf-values-accumulations';
    $command = <<<SH
        cd {$PYTHON_SCRIPT_PROJECT_PATH} && poetry run python ./generate_radaric_mf_values_accumulations/main.py --timestamp {$timestamp} >> /var/log/infoclimat/generate-radaric-mf-values-accumulations.log 2>> /var/log/infoclimat/generate-radaric-mf-values-accumulations.error.log
        SH;
    $outputer->echo("Running : {$command}\n");
    $outputer->echo($command_executor->shell_exec($command) ?? '');
}

function convert_hd5_to_colored_tif(
    string                        $zone,
    int                           $timestamp,
    bool                          $replace_existing,
    CommandExecutor               $command_executor,
    FileExistanceChecker          $file_existance_checker,
    FileMover                     $file_mover,
    LastTilesTimestampsRepository $last_tiles_timestamps_repository,
    Outputer                      $outputer = new FakeOutputer()
): void {
    $h5_file_path = get_h5_path($zone, $timestamp);
    if (!$file_existance_checker->isFile($h5_file_path)) {
        $datetime = gmdate('Y-m-d H:i:s', $timestamp);
        $outputer->echo(
            <<<TXT
                Skipping {$zone} at {$datetime} :
                    '{$h5_file_path}' does not exist !\n
                TXT
        );
        return;
    }
    $tif_file_path = get_tif_path($zone, $timestamp);
    $colored_file_path = get_colored_tif_path($zone, $timestamp);
    convert_h5_to_tif(
        $h5_file_path,
        $tif_file_path,
        $replace_existing,
        $command_executor,
        $file_existance_checker,
        $file_mover,
        $outputer
    );
    color_tif(
        $tif_file_path,
        $colored_file_path,
        $replace_existing,
        $command_executor,
        $file_existance_checker,
        $file_mover,
        $outputer
    );

    if (!$replace_existing) {
        $key = get_radaric_key($zone);
        $last_tiles_timestamps_repository->updateLastTileTimestamp($key, $timestamp);
    }
}

/**
 * @param string[] $zones
 */
function convert_hd5_to_colored_tif_from_zones(
    array                         $zones,
    int                           $timestamp,
    bool                          $replace_existing,
    CommandExecutor               $command_executor,
    FileExistanceChecker          $file_existance_checker,
    FileMover                     $file_mover,
    LastTilesTimestampsRepository $last_tiles_timestamps_repository,
    Outputer                      $outputer = new FakeOutputer()
): void {
    foreach ($zones as $zone) {
        convert_hd5_to_colored_tif(
            $zone,
            $timestamp,
            $replace_existing,
            $command_executor,
            $file_existance_checker,
            $file_mover,
            $last_tiles_timestamps_repository,
            $outputer
        );
    }
}

function convert_hd5_to_colored_tif_from_all_zones(
    int                           $timestamp,
    bool                          $replace_existing,
    CommandExecutor               $command_executor,
    FileExistanceChecker          $file_existance_checker,
    FileMover                     $file_mover,
    LastTilesTimestampsRepository $last_tiles_timestamps_repository,
    Outputer                      $outputer = new FakeOutputer()
): void {
    convert_hd5_to_colored_tif_from_zones(
        ZONES,
        $timestamp,
        $replace_existing,
        $command_executor,
        $file_existance_checker,
        $file_mover,
        $last_tiles_timestamps_repository,
        $outputer
    );
}

class ConversionArguments
{
    public int   $start;
    public int   $end;
    public array $zones;
    public bool  $replace;

    public function __construct(
        int   $start,
        int   $end,
        array $zones,
        bool  $replace
    ) {
        $this->start = $start;
        $this->end = $end;
        $this->zones = $zones;
        $this->replace = $replace;
    }
}

function convert_hd5_to_colored_tif_from_zone_in_range(
    string                        $zone,
    ConversionArguments           $conversion_arguments,
    CommandExecutor               $command_executor,
    FileExistanceChecker          $file_existance_checker,
    FileMover                     $file_mover,
    LastTilesTimestampsRepository $last_tiles_timestamps_repository,
    Outputer                      $outputer = new FakeOutputer()
): void {
    for (
        $timestamp = $conversion_arguments->start;
        $timestamp <= $conversion_arguments->end;
        $timestamp += mn(5)->inSeconds()
    ) {
        convert_hd5_to_colored_tif(
            $zone,
            $timestamp,
            $conversion_arguments->replace,
            $command_executor,
            $file_existance_checker,
            $file_mover,
            $last_tiles_timestamps_repository,
            $outputer
        );
    }
}

function convert_hd5_to_colored_tif_from_zones_in_range(
    ConversionArguments           $conversion_arguments,
    CommandExecutor               $command_executor,
    FileExistanceChecker          $file_existance_checker,
    FileMover                     $file_mover,
    LastTilesTimestampsRepository $last_tiles_timestamps_repository,
    Outputer                      $outputer = new FakeOutputer()
): void {
    foreach ($conversion_arguments->zones as $zone) {
        convert_hd5_to_colored_tif_from_zone_in_range(
            $zone,
            $conversion_arguments,
            $command_executor,
            $file_existance_checker,
            $file_mover,
            $last_tiles_timestamps_repository,
            $outputer
        );
    }
}

function convert_hd5_to_colored_tif_from_all_zones_in_range(
    ConversionArguments           $conversion_arguments,
    CommandExecutor               $command_executor,
    FileExistanceChecker          $file_existance_checker,
    FileMover                     $file_mover,
    LastTilesTimestampsRepository $last_tiles_timestamps_repository,
    Outputer                      $outputer = new FakeOutputer()
): void {
    $conversion_arguments->zones = ZONES;
    convert_hd5_to_colored_tif_from_zones_in_range(
        $conversion_arguments,
        $command_executor,
        $file_existance_checker,
        $file_mover,
        $last_tiles_timestamps_repository,
        $outputer
    );
}

function convert_hd5_to_colored_tif_and_compute_cumuls(
    string                        $zone,
    int                           $timestamp,
    bool                          $replace_existing,
    CommandExecutor               $command_executor,
    FileExistanceChecker          $file_existance_checker,
    FileMover                     $file_mover,
    LastTilesTimestampsRepository $last_tiles_timestamps_repository,
    Outputer                      $outputer = new FakeOutputer()
): void {
    convert_hd5_to_colored_tif(
        $zone,
        $timestamp,
        $replace_existing,
        $command_executor,
        $file_existance_checker,
        $file_mover,
        $last_tiles_timestamps_repository,
        $outputer
    );
    compute_cumuls(
        $zone,
        $timestamp,
        $command_executor,
        $outputer
    );
}

function get_last_timestamp(LastTilesTimestampsRepository $last_tiles_timestamps_repository): int
{
    $key = get_file_key(LAME_D_EAU, 'METROPOLE');
    return $last_tiles_timestamps_repository->getLastTileTimestamp($key);
}

function parse_range_argument(int|string|null $datetime_or_timestamp): ?int
{
    if (!$datetime_or_timestamp) {
        return null;
    }
    return is_numeric($datetime_or_timestamp)
        ? (int) $datetime_or_timestamp
        : strtotime($datetime_or_timestamp);
}

function parse_start_argument(
    bool                          $last,
    int|string|null               $datetime_or_timestamp,
    LastTilesTimestampsRepository $last_tiles_timestamps_repository
): ?int {
    if ($last) {
        return get_last_timestamp($last_tiles_timestamps_repository);
    }
    if (!$datetime_or_timestamp) {
        return null;
    }
    return parse_range_argument($datetime_or_timestamp);
}

function get_end_timestamp(
    int|string|null $end,
    int             $start_timestamp,
    Outputer        $outputer = new FakeOutputer()
): ?int {
    $end_timestamp = parse_range_argument($end);
    if ($end_timestamp) {
        return $end_timestamp;
    }
    $outputer->echo("No --end argument given. Defaulting to --start.\n");
    return $start_timestamp;
}

/**
 * @param string|string[]|null $zone
 * @return string[]|null
 */
function parse_zone_argument(
    array|string|null $zone,
    Outputer          $outputer = new FakeOutputer()
): ?array {
    if (!$zone) {
        return null;
    }
    $zones = is_array($zone) ? $zone : [$zone];
    $valid_zones = [];
    $valid_choices = implode(', ', ZONES);
    foreach ($zones as $zone) {
        if (!in_array($zone, ZONES)) {
            $outputer->echo("Invalid zone: {$zone}. Valid zones are {$valid_choices}.\n");
        } else {
            $valid_zones[] = $zone;
        }
    }
    return $valid_zones;
}

/**
 * @param string|string[]|null $zone
 */
function get_zones(
    array|string|null $zone,
    Outputer          $outputer = new FakeOutputer()
): array {
    $zones = parse_zone_argument($zone, $outputer);
    if ($zones !== null) {
        return $zones;
    }
    $valid_choices = implode(', ', ZONES);
    $outputer->echo("No --zone argument given. Defaulting to all zones ({$valid_choices}).\n");
    return ZONES;
}

function parse_replace_existing_argument(bool|string|null $replace): bool
{
    if ($replace === null) {
        return false;
    }
    if ($replace === false) {
        /**
         * Faut pas chercher, c'est la logique de PHP.
         * Si l'argument est présent mais n'a pas de valeur, alors il vaut false.
         * Il ne vaudra jamais true.
         */
        return true;
    }
    return $replace === 'true';
}

function get_arguments(): array
{
    return getopt('', [
        'last',
        'datetime:',
        'timestamp:',
        'start:',
        'end:',
        'zone:',
        'replace::',
        'help',
    ]);
}

function get_conversion_arguments_from(
    array                         $arguments,
    LastTilesTimestampsRepository $last_tiles_timestamps_repository,
    Outputer                      $outputer = new FakeOutputer()
): ?ConversionArguments {
    $start_timestamp = parse_start_argument(
        array_key_exists('last', $arguments),
        $arguments['datetime'] ?? $arguments['timestamp'] ?? $arguments['start'] ?? null,
        $last_tiles_timestamps_repository
    );
    if (!$start_timestamp) {
        $outputer->echo(
            <<<TXT
                Missing (--start|--timestamp|--datetime|--last) argument :
                    - --start=timestamp
                    - --start='YYYY-MM-DD hh:mm:ss'
                    - --timestamp=timestamp (--end will be set to --timestamp)
                    - --datetime='YYYY-MM-DD hh:mm:ss' (--end will be set to --datetime)
                    - --last (--start and --end will be set to the last available tiles timestamps)\n
                TXT
        );
        return null;
    }

    $end_timestamp = get_end_timestamp(
        $arguments['end'] ?? null,
        $start_timestamp,
        $outputer
    );

    $zones = get_zones($arguments['zone'] ?? null, $outputer);

    $replace_existing = parse_replace_existing_argument($arguments['replace'] ?? null);

    return new ConversionArguments(
        $start_timestamp,
        $end_timestamp,
        $zones,
        $replace_existing
    );
}

interface ArgumentsGetter
{
    public function getArguments(): array;
}

class RealArgumentsGetter implements ArgumentsGetter
{
    public function getArguments(): array
    {
        return get_arguments();
    }
}

class InMemoryArgumentsGetter implements ArgumentsGetter
{
    private array $arguments = [];

    public function __construct(array $arguments = [])
    {
        $this->arguments = $arguments;
    }

    public function getArguments(): array
    {
        return $this->arguments;
    }
}

const HELP_MESSAGE = <<<TXT
          Usage:
              php convert-from-args.php (--last | --datetime='YYYY-MM-DD hh:mm:ss' | --timestamp=timestamp | --start='YYYY-MM-DD hh:mm:ss'|timestamp) [--end='YYYY-MM-DD hh:mm:ss'|timestamp]? [--zone=(METROPOLE|ANTILLES|REUNION|NOUVELLE-CALEDONIE)]* [--replace(=true)?]?
          
          Options:
              --last
                  Use the last available tiles timestamps as --start and --end.
          
              --datetime='YYYY-MM-DD hh:mm:ss'
                  Set --start and --end to the same given datetime.
          
              --timestamp=timestamp
                  Set --start and --end to the same given timestamp.
          
              --start='YYYY-MM-DD hh:mm:ss'
                  Set --start to the given datetime.
          
              --start=timestamp
                  Set --start to the given timestamp.
          
              --end='YYYY-MM-DD hh:mm:ss'
                  Set --end to the given datetime.
          
              --end=timestamp
                  Set --end to the given timestamp.
          
              --zone=(METROPOLE|ANTILLES|REUNION|NOUVELLE-CALEDONIE) [--zone=...]*
                  Set the zone to convert. Can be used multiple times.
          
              --replace(=true)?
                  Replace existing files. If no value is given, it defaults to true.
                  Settings this to anything other than true will disable replacing.
          
              --help
                  Display this help message.\n
          TXT;

function execute_conversion_from_arguments(
    CommandExecutor               $command_executor,
    FileExistanceChecker          $file_existance_checker,
    ArgumentsGetter               $arguments_getter,
    LastTilesTimestampsRepository $last_tiles_timestamps_repository,
    FileMover                     $file_mover,
    Outputer                      $outputer = new FakeOutputer()
): void {
    $arguments = $arguments_getter->getArguments();

    if (array_key_exists('help', $arguments)) {
        $outputer->echo(HELP_MESSAGE);
        return;
    }

    $conversion_arguments = get_conversion_arguments_from(
        $arguments,
        $last_tiles_timestamps_repository,
        $outputer
    );

    if (!$conversion_arguments) {
        $outputer->echo(HELP_MESSAGE);
        return;
    }

    convert_hd5_to_colored_tif_from_zones_in_range(
        $conversion_arguments,
        $command_executor,
        $file_existance_checker,
        $file_mover,
        $last_tiles_timestamps_repository,
        $outputer
    );
}

function real_execute_conversion_from_arguments(): void
{
    execute_conversion_from_arguments(
        new RealCommandExecutor(),
        new RealFileExistanceChecker(),
        new RealArgumentsGetter(),
        new RealLastTilesTimestampsRepository(),
        new RealFileMover(),
        new RealOutputer()
    );
}

function execute_download_and_conversion(
    bool                          $replace_existing,
    CommandExecutor               $command_executor,
    APIFileDownloader             $api_file_downloader,
    FileAppender                  $file_appender,
    FileMover                     $file_mover,
    LastTilesTimestampsRepository $last_tiles_timestamps_repository,
    FileExistanceChecker          $file_existance_checker,
    Outputer                      $outputer = new FakeOutputer()
): void {
    execute_download(
        $replace_existing,
        $api_file_downloader,
        $file_appender,
        $file_mover,
        $last_tiles_timestamps_repository,
        $outputer
    );

    convert_hd5_to_colored_tif_from_all_zones(
        get_last_timestamp($last_tiles_timestamps_repository),
        $replace_existing,
        $command_executor,
        $file_existance_checker,
        $file_mover,
        $last_tiles_timestamps_repository,
        $outputer
    );
}

function real_execute_download_and_conversion(): void
{
    execute_download_and_conversion(
        false,
        new RealCommandExecutor(),
        new RealAPIFileDownloader(),
        new RealFileAppender(),
        new RealFileMover(),
        new RealLastTilesTimestampsRepository(),
        new RealFileExistanceChecker(),
        new RealOutputer()
    );
}

function execute_download_conversion_and_generate_accumulations(
    bool                          $replace_existing,
    CommandExecutor               $command_executor,
    APIFileDownloader             $api_file_downloader,
    FileAppender                  $file_appender,
    FileMover                     $file_mover,
    LastTilesTimestampsRepository $last_tiles_timestamps_repository,
    FileExistanceChecker          $file_existance_checker,
    Outputer                      $outputer = new FakeOutputer()
): void {
    execute_download(
        $replace_existing,
        $api_file_downloader,
        $file_appender,
        $file_mover,
        $last_tiles_timestamps_repository,
        $outputer
    );

    $timestamp = get_last_timestamp($last_tiles_timestamps_repository);

    convert_hd5_to_colored_tif_from_all_zones(
        $timestamp,
        $replace_existing,
        $command_executor,
        $file_existance_checker,
        $file_mover,
        $last_tiles_timestamps_repository,
        $outputer
    );

    compute_cumuls_from_all_zones(
        $timestamp,
        $command_executor,
        $outputer
    );
}

function real_execute_download_conversion_and_generate_accumulations(): void
{
    execute_download_conversion_and_generate_accumulations(
        false,
        new RealCommandExecutor(),
        new RealAPIFileDownloader(),
        new RealFileAppender(),
        new RealFileMover(),
        new RealLastTilesTimestampsRepository(),
        new RealFileExistanceChecker(),
        new RealOutputer()
    );
}
