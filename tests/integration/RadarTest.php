<?php

declare(strict_types=1);

namespace Infoclimat\Radar\Tests\Integration;

require_once __ROOT__ . '/env.php';
require_once __ROOT__ . '/meteofrance-api.php';
require_once __ROOT__ . '/radar.php';
require_once __ROOT__ . '/io.php';

use Infoclimat\IO\RealOutputer;
use Infoclimat\MeteoFrance\API\RealAPIFileDownloader;
use Infoclimat\Tiles\RealLastTilesTimestampsRepository;
use PHPUnit\Framework\TestCase;

use function Infoclimat\Radar\download_file;
use function Infoclimat\Radar\get_previous_last_timestamp;

use const Infoclimat\Radar\LAME_D_EAU;

final class RadarTest extends TestCase
{
    public function testDownloadFileIntegration(): void
    {
        $zone = 'METROPOLE';
        $data_type = LAME_D_EAU;
        $maille = 500;
        $path = "/tmp/mosaiques_MF_{$data_type}_{$zone}_integration_test.h5";
        $api_file_downloader = new RealAPIFileDownloader();
        $outputer = new RealOutputer();

        if (file_exists($path)) {
            unlink($path);
        }

        $curl_response = download_file(
            $path,
            $zone,
            $data_type,
            $maille,
            $api_file_downloader,
            $outputer,
            2,
            2
        );

        $this->assertFileExists($path, 'Downloaded file should exist');
        $this->assertEquals(200, $curl_response->code, 'HTTP response code should be 200');
        $this->assertEmpty($curl_response->error, 'Curl error should be empty');
    }

    public function testGetPreviousLastTimestamp(): void
    {
        $data_type = LAME_D_EAU;
        $zone = 'METROPOLE';
        $last_tiles_timestamps_repository = new RealLastTilesTimestampsRepository();
        $actual_timestamp = get_previous_last_timestamp(
            $data_type,
            $zone,
            $last_tiles_timestamps_repository
        );
        $now = time();
        $this->assertLessThanOrEqual(60 * 60, $now - $actual_timestamp, 'Last timestamp should be less than 1 hour ago');
    }
}
