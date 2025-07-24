<?php

declare(strict_types=1);

namespace Infoclimat\Radar;

require_once __DIR__ . '/env.php';
require_once __DIR__ . '/date.php';
require_once __DIR__ . '/io.php';
require_once __DIR__ . '/meteofrance-api.php';
require_once __DIR__ . '/tiles.php';

use DateTime;
use DateTimeZone;
use Exception;
use Infoclimat\IO\FakeOutputer;
use Infoclimat\IO\Outputer;
use Infoclimat\IO\RealOutputer;
use Infoclimat\MeteoFrance\API\APIFileDownloader;
use Infoclimat\MeteoFrance\API\CurlResponse;
use Infoclimat\MeteoFrance\API\RealAPIFileDownloader;
use Infoclimat\Tiles\LastTilesTimestampsRepository;
use Infoclimat\Tiles\RealLastTilesTimestampsRepository;

use function Infoclimat\Date\hh_of;
use function Infoclimat\Date\ii_of;

use const Infoclimat\Env\TILES_PATH;

// contact.api@meteo.fr
const API_URL = 'https://public-api.meteofrance.fr/public/DPRadar/v1/mosaiques';

const ZONES = [
    'ANTILLES',
    'REUNION',
    'METROPOLE',
    // 'NOUVELLE-CALEDONIE',
];

const LAME_D_EAU = 'LAME_D_EAU';
const REFLECTIVITE = 'REFLECTIVITE';
const DATA_TYPES = [LAME_D_EAU, REFLECTIVITE];

const MAILLES = [500, 1000];

function get_file_endpoint(
    string $zone,
    string $data_type,
    int    $maille
): string {
    return API_URL . "/{$zone}/observations/{$data_type}/produit?maille={$maille}";
}

function is_mf_bug(CurlResponse $curl_response): bool
{
    return (
        in_array($curl_response->error_code, [56, 104])
        || $curl_response->code === 400
        || $curl_response->code >= 500
    );
}

/**
 * @throws Exception
 */
function download_file(
    string            $path,
    string            $zone,
    string            $data_type,
    int               $maille,
    APIFileDownloader $api_file_downloader,
    Outputer          $outputer = new FakeOutputer(),
    int               $max_attempts = 5,
    int               $sleep_time = 5
): CurlResponse {
    $url = get_file_endpoint($zone, $data_type, $maille);
    $outputer->echo("Downloading {$data_type} of {$zone} (maille {$maille}) [{$url}] to {$path}\n");
    for ($attemp = 0; $attemp < $max_attempts; $attemp++) {
        $curl_response = $api_file_downloader->downloadAPIFile($path, $url);
        if (is_mf_bug($curl_response)) {
            $outputer->echo(format_curl_response($curl_response) . "\n");
            sleep($sleep_time);
            continue;
        }
        return $curl_response;
    }
    throw new Exception("Failed to download {$data_type} of {$zone} (maille {$maille}) [{$url}] after {$max_attempts} attempts.");
}

function format_curl_response(CurlResponse $curl_response): string
{
    $headers = json_encode($curl_response->headers);
    return <<<TXT
        CurlResponse(
            code = {$curl_response->code},
            response = '{$curl_response->response}',
            headers = {$headers},
            error_code = {$curl_response->error_code},
            error = '{$curl_response->error}'
        )
        TXT;
}

function get_content_disposition_error_log(
    string       $zone,
    string       $data_type,
    int          $maille,
    CurlResponse $curl_response
): string {
    $response = format_curl_response($curl_response);
    return <<<TXT
        Zone = {$zone}, Type = {$data_type}, Maille = {$maille}, Response = {$response}
        TXT;
}

function append_file(string $path, string $data): void
{
    file_put_contents($path, "{$data}\n", FILE_APPEND);
}

interface FileAppender
{
    public function appendFile(string $path, string $data): void;
}

class RealFileAppender implements FileAppender
{
    public function appendFile(string $path, string $data): void
    {
        append_file($path, $data);
    }
}

class InMemoryFileAppender implements FileAppender
{
    public array $files = [];

    public function appendFile(string $path, string $data): void
    {
        $this->files[$path][] = $data;
    }
}

function log_content_disposition_error(
    string       $zone,
    string       $data_type,
    int          $maille,
    CurlResponse $curl_response,
    FileAppender $file_appender,
    Outputer     $outputer = new FakeOutputer()
): void {
    $log_file = '/var/log/infoclimat/radar.log';
    $log = get_content_disposition_error_log(
        $zone,
        $data_type,
        $maille,
        $curl_response
    );
    $outputer->echo("ERROR : {$log}\n");
    $file_appender->appendFile($log_file, $log);
}

/**
 * 'attachment; filename="T_IPRN20_C_LFPW_20000615123045.h5"
 */
function extract_date_part_from_content_disposition(string $content_disposition): string
{
    return substr($content_disposition, -strlen('YYYYMMDDhhmmss.h5"'), strlen('YYYYMMDDhhmmss'));
}

function get_datetime_from_date_part($YYYYMMDDhhmmss): DateTime|false
{
    return DateTime::createFromFormat('YmdHis', $YYYYMMDDhhmmss, new DateTimeZone('UTC'));
}

/**
 * 'attachment; filename="T_IPRN20_C_LFPW_20000615123045.h5"
 */
function get_timestamp_from_content_disposition(
    string   $content_disposition,
    Outputer $outputer = new FakeOutputer()
): int {
    $YYYYMMDDhhmmss = extract_date_part_from_content_disposition($content_disposition);
    $datetime = get_datetime_from_date_part($YYYYMMDDhhmmss);
    $outputer->echo("Date from content-disposition header is : {$YYYYMMDDhhmmss} ({$datetime->format('Y-m-d H:i:s')} UTC [{$datetime->getTimestamp()}])\n");
    return $datetime->getTimestamp();
}

function get_tile_path(string $key, int $timestamp, string $ext): string
{
    $YYYY_MM_DD = gmdate('Y/m/d', $timestamp);
    $hh = hh_of($timestamp);
    $mm = ii_of($timestamp);
    return TILES_PATH . "/{$YYYY_MM_DD}/{$key}_{$hh}_v{$mm}.{$ext}";
}

function get_file_key(string $data_type, string $zone): string
{
    return "mosaiques_MF_{$data_type}_{$zone}";
}

function get_file_path(
    int    $timestamp,
    string $data_type,
    string $zone
): string {
    $file_key = get_file_key($data_type, $zone);
    return get_tile_path($file_key, $timestamp, 'h5');
}

function get_previous_last_timestamp(
    string                        $data_type,
    string                        $zone,
    LastTilesTimestampsRepository $last_tiles_timestamps_repository
): ?int {
    $key = get_file_key($data_type, $zone);
    return $last_tiles_timestamps_repository->getLastTileTimestamp($key);
}

function update_last_timestamp(
    string                        $data_type,
    string                        $zone,
    int                           $timestamp,
    LastTilesTimestampsRepository $last_tiles_timestamps_repository,
    Outputer                      $outputer = new FakeOutputer()
): void {
    $key = get_file_key($data_type, $zone);
    $outputer->echo("Updating {$key} to {$timestamp}\n");
    $last_tiles_timestamps_repository->updateLastTileTimestamp($key, $timestamp);
}

function create_folder_if_needed(
    string   $file_path,
    Outputer $outputer = new FakeOutputer()
): void {
    $dir = dirname($file_path);
    if (!is_dir($dir)) {
        mkdir($dir, 0777, true);
        $outputer->echo("Creating folder : {$dir}\n");
    }
}

function move_file(
    string   $from,
    string   $to,
    Outputer $outputer = new FakeOutputer()
): void {
    create_folder_if_needed($to, $outputer);
    rename($from, $to);
    $outputer->echo("Moving {$from} to {$to}\n");
}

interface FileMover
{
    public function moveFile(string $from, string $to, ?Outputer $outputer): void;
}

class RealFileMover implements FileMover
{
    public function moveFile(
        string    $from,
        string    $to,
        ?Outputer $outputer = new FakeOutputer()
    ): void {
        move_file($from, $to, $outputer);
    }
}

class InMemoryFileMover implements FileMover
{
    public array $moved = [];

    public function moveFile(
        string    $from,
        string    $to,
        ?Outputer $outputer = new FakeOutputer()
    ): void {
        $this->moved[] = [$from, $to];
        $outputer->echo("Moving {$from} to {$to}\n");
    }
}

/**
 * @throws Exception
 */
function download_data_type_for_zone(
    string                        $zone,
    string                        $data_type,
    int                           $maille,
    bool                          $replace_existing,
    APIFileDownloader             $api_file_downloader,
    FileAppender                  $file_appender,
    FileMover                     $file_mover,
    LastTilesTimestampsRepository $last_tiles_timestamps_repository,
    Outputer                      $outputer = new FakeOutputer()
): void {
    $tmp_path = "/tmp/mosaiques_MF_{$data_type}_{$zone}_last.h5";
    $curl_response = download_file(
        $tmp_path,
        $zone,
        $data_type,
        $maille,
        $api_file_downloader,
        $outputer
    );
    $content_disposition = $curl_response->headers['content-disposition'] ?? null;
    if (!$content_disposition) {
        log_content_disposition_error(
            $zone,
            $data_type,
            $maille,
            $curl_response,
            $file_appender,
            $outputer
        );
        $outputer->echo("{$data_type} of {$zone} : ERROR\n\n");
        return;
    }
    $timestamp = get_timestamp_from_content_disposition($content_disposition, $outputer);
    $previous_last_timestamp = get_previous_last_timestamp(
        $data_type,
        $zone,
        $last_tiles_timestamps_repository
    );
    if ($previous_last_timestamp && $previous_last_timestamp >= $timestamp) {
        if (!$replace_existing) {
            $outputer->echo("Skipping {$data_type} of {$zone} (maille {$maille}) at {$timestamp} because it is not newer than {$previous_last_timestamp} and replace mode is not active.\n");
            $outputer->echo("{$data_type} of {$zone} at {$timestamp} : SKIPPED\n\n");
            return;
        }
        $outputer->echo("Replacing existing {$data_type} of {$zone} (maille {$maille}) at {$timestamp}. Last timestamp was {$previous_last_timestamp}.\n");
    }
    $final_path = get_file_path($timestamp, $data_type, $zone);
    $file_mover->moveFile($tmp_path, $final_path, $outputer);
    if (!$replace_existing) {
        update_last_timestamp(
            $data_type,
            $zone,
            $timestamp,
            $last_tiles_timestamps_repository,
            $outputer
        );
    }
    $outputer->echo("{$data_type} of {$zone} at {$timestamp} : DONE\n\n");
}

function download_data_type(
    string                        $data_type,
    int                           $maille,
    bool                          $replace_existing,
    APIFileDownloader             $api_file_downloader,
    FileAppender                  $file_appender,
    FileMover                     $file_mover,
    LastTilesTimestampsRepository $last_tiles_timestamps_repository,
    Outputer                      $outputer = new FakeOutputer()
): void {
    foreach (ZONES as $zone) {
        try {
            download_data_type_for_zone(
                $zone,
                $data_type,
                $maille,
                $replace_existing,
                $api_file_downloader,
                $file_appender,
                $file_mover,
                $last_tiles_timestamps_repository,
                $outputer
            );
        } catch (Exception $e) {
            $outputer->echo(
                <<<TXT
An error occurred while downloading {$data_type} of {$zone} (maille {$maille}) :
{$e->getMessage()}

TXT
            );
        }
    }
}

function download_lame_d_eau(
    bool                          $replace_existing,
    APIFileDownloader             $api_file_downloader,
    FileAppender                  $file_appender,
    FileMover                     $file_mover,
    LastTilesTimestampsRepository $last_tiles_timestamps_repository,
    Outputer                      $outputer = new FakeOutputer()
): void {
    $data_type = LAME_D_EAU;
    $maille = 500;
    download_data_type(
        $data_type,
        $maille,
        $replace_existing,
        $api_file_downloader,
        $file_appender,
        $file_mover,
        $last_tiles_timestamps_repository,
        $outputer
    );
}

function execute_download(
    bool                          $replace_existing,
    APIFileDownloader             $api_file_downloader,
    FileAppender                  $file_appender,
    FileMover                     $file_mover,
    LastTilesTimestampsRepository $last_tiles_timestamps_repository,
    Outputer                      $outputer = new FakeOutputer()
): void {
    download_lame_d_eau(
        $replace_existing,
        $api_file_downloader,
        $file_appender,
        $file_mover,
        $last_tiles_timestamps_repository,
        $outputer
    );
}

function real_execute_download(): void
{
    execute_download(
        false,
        new RealAPIFileDownloader(),
        new RealFileAppender(),
        new RealFileMover(),
        new RealLastTilesTimestampsRepository(),
        new RealOutputer()
    );
}
