<?php

declare(strict_types=1);

namespace Infoclimat\Radar\Tests\Unit;

require_once __ROOT__ . '/env.php';
require_once __ROOT__ . '/meteofrance-api.php';
require_once __ROOT__ . '/radar.php';
require_once __ROOT__ . '/io.php';

use Exception;
use Infoclimat\IO\FakeOutputer;
use Infoclimat\IO\InMemoryFileMover;
use Infoclimat\MeteoFrance\API\CurlResponse;
use Infoclimat\MeteoFrance\API\InMemoryAPIFileDownloader;
use Infoclimat\Radar\InMemoryFileAppender;
use Infoclimat\Tiles\InMemoryLastTilesTimestampsRepository;
use PHPUnit\Framework\TestCase;

use function Infoclimat\IO\create_folder_if_needed;
use function Infoclimat\IO\move_file;
use function Infoclimat\Radar\download_data_type;
use function Infoclimat\Radar\download_data_type_for_zone;
use function Infoclimat\Radar\download_file;
use function Infoclimat\Radar\format_curl_response;
use function Infoclimat\Radar\get_content_disposition_error_log;
use function Infoclimat\Radar\get_file_endpoint;
use function Infoclimat\Radar\get_file_key;
use function Infoclimat\Radar\get_file_path;
use function Infoclimat\Radar\get_previous_last_timestamp;
use function Infoclimat\Radar\get_timestamp_from_content_disposition;
use function Infoclimat\Radar\update_last_timestamp;

use const Infoclimat\Env\TILES_PATH;

final class RadarTest extends TestCase
{
    public function testGetFileEndpoint(): void
    {
        $zone = 'METROPOLE';
        $data_type = 'LAME_D_EAU';
        $maille = 500;
        $this->assertSame(
            'https://public-api.meteofrance.fr/public/DPRadar/v1/mosaiques/METROPOLE/observations/LAME_D_EAU/produit?maille=500',
            get_file_endpoint($zone, $data_type, $maille)
        );
    }

    public function testDownloadFile(): void
    {
        $path = '/my/path';
        $zone = 'METROPOLE';
        $data_type = 'LAME_D_EAU';
        $maille = 500;
        $curl_response = new CurlResponse(200, '', ['content-disposition' => 'attachment; filename="T_IPRN20_C_LFPW_20000615123045.h5"']);
        $api_file_downloader = new InMemoryAPIFileDownloader([
            'https://public-api.meteofrance.fr/public/DPRadar/v1/mosaiques/METROPOLE/observations/LAME_D_EAU/produit?maille=500' => $curl_response,
        ]);
        $outputer = new FakeOutputer();
        $response = download_file(
            $path,
            $zone,
            $data_type,
            $maille,
            $api_file_downloader,
            $outputer
        );
        $this->assertSame($curl_response, $response);
        $this->assertSame(
            [
                [
                    'path'    => '/my/path',
                    'url'     => 'https://public-api.meteofrance.fr/public/DPRadar/v1/mosaiques/METROPOLE/observations/LAME_D_EAU/produit?maille=500',
                    'headers' => [],
                    'options' => [],
                ],
            ],
            $api_file_downloader->requests
        );
        $this->assertSame(
            <<<TXT
                Downloading LAME_D_EAU of METROPOLE (maille 500) [https://public-api.meteofrance.fr/public/DPRadar/v1/mosaiques/METROPOLE/observations/LAME_D_EAU/produit?maille=500] to /my/path\n
                TXT,
            $outputer->output
        );
    }

    public function testDownloadFileFailsAfterMaxAttempts(): void
    {
        $path = '/my/path';
        $zone = 'METROPOLE';
        $data_type = 'LAME_D_EAU';
        $maille = 500;
        $curl_response = new CurlResponse(200, '', [], 56, 'error');
        $api_file_downloader = new InMemoryAPIFileDownloader([
            'https://public-api.meteofrance.fr/public/DPRadar/v1/mosaiques/METROPOLE/observations/LAME_D_EAU/produit?maille=500' => $curl_response,
        ]);
        $outputer = new FakeOutputer();
        $this->expectException(Exception::class);
        $this->expectExceptionMessage('Failed to download LAME_D_EAU of METROPOLE (maille 500) [https://public-api.meteofrance.fr/public/DPRadar/v1/mosaiques/METROPOLE/observations/LAME_D_EAU/produit?maille=500] after 5 attempts.');
        download_file(
            $path,
            $zone,
            $data_type,
            $maille,
            $api_file_downloader,
            $outputer,
            5,
            0
        );
    }

    public function testFormatCurlResponse(): void
    {
        $timestamp = format_curl_response(new CurlResponse(200, 'txt', ['key' => 'value']));
        $expected = <<<TXT
            CurlResponse(
                code = 200,
                response = 'txt',
                headers = {"key":"value"},
                error_code = 0,
                error = ''
            )
            TXT;
        $this->assertSame($expected, $timestamp);
    }

    public function testGetContentDispositionErrorLog(): void
    {
        $zone = 'METROPOLE';
        $data_type = 'LAME_D_EAU';
        $maille = 500;
        $curl_response = new CurlResponse(200, 'txt', ['key' => 'value']);
        $timestamp = get_content_disposition_error_log(
            $zone,
            $data_type,
            $maille,
            $curl_response
        );
        $expected = <<<TXT
            Zone = METROPOLE, Type = LAME_D_EAU, Maille = 500, Response = CurlResponse(
                code = 200,
                response = 'txt',
                headers = {"key":"value"},
                error_code = 0,
                error = ''
            )
            TXT;
        $this->assertSame($expected, $timestamp);
    }

    public function testGetTimestampFromContentDisposition(): void
    {
        $outputer = new FakeOutputer();
        $timestamp = get_timestamp_from_content_disposition(
            'attachment; filename="T_IPRN20_C_LFPW_20000615123045.h5"',
            $outputer
        );
        $this->assertSame(strtotime('2000-06-15T12:30:45Z'), $timestamp);
        $this->assertSame(
            "Date from content-disposition header is : 20000615123045 (2000-06-15 12:30:45 UTC [961072245])\n",
            $outputer->output
        );
    }

    public function testGetFileKey(): void
    {
        $this->assertSame(
            'mosaiques_MF_LAME_D_EAU_METROPOLE',
            get_file_key('LAME_D_EAU', 'METROPOLE')
        );
    }

    public function testGetFilePath(): void
    {
        $timestamp = strtotime('2000-06-15T12:30:45Z');
        $data_type = 'LAME_D_EAU';
        $zone = 'METROPOLE';
        $this->assertSame(
            TILES_PATH . '/2000/06/15/mosaiques_MF_LAME_D_EAU_METROPOLE_12_v30.h5',
            get_file_path($timestamp, $data_type, $zone)
        );
    }

    public function testGetPreviousLastTimestamp(): void
    {
        $timestamp = strtotime('2000-06-15T12:30:45Z');
        $repository = new InMemoryLastTilesTimestampsRepository([
            'mosaiques_MF_LAME_D_EAU_METROPOLE' => $timestamp,
        ]);
        $previous = get_previous_last_timestamp('LAME_D_EAU', 'METROPOLE', $repository);
        $this->assertSame($timestamp, $previous);
    }

    public function testUpdateLastTimestamp(): void
    {
        $timestamp = strtotime('2000-06-15T12:30:45Z');
        $repository = new InMemoryLastTilesTimestampsRepository();
        $outputer = new FakeOutputer();
        update_last_timestamp(
            'LAME_D_EAU',
            'METROPOLE',
            $timestamp,
            $repository,
            $outputer
        );
        $this->assertSame(
            ['mosaiques_MF_LAME_D_EAU_METROPOLE' => $timestamp],
            $repository->timestamps
        );
        $this->assertSame(
            "Updating mosaiques_MF_LAME_D_EAU_METROPOLE to 961072245\n",
            $outputer->output
        );
    }

    public function testCreateFolderIfNeededCreatesDirectory(): void
    {
        $base_dir = '/tmp/radar_test_create_folder';
        $sub_dir = "{$base_dir}/subdir";
        $file_path = "{$sub_dir}/testfile.txt";
        $outputer = new FakeOutputer();

        if (is_dir($sub_dir)) {
            rmdir($sub_dir);
        }

        $this->assertFalse(is_dir($sub_dir), 'Directory should not exist before calling create_folder_if_needed');

        create_folder_if_needed($file_path, $outputer);

        $this->assertTrue(is_dir($sub_dir), 'Directory should be created by create_folder_if_needed');
        $this->assertEquals("Creating folder : /tmp/radar_test_create_folder/subdir\n", $outputer->output, 'Outputer should contain creation message');
    }

    public function testCreateFolderIfNeededDirectoryAlreadyExists(): void
    {
        $base_dir = '/tmp/radar_test_create_folder';
        $sub_dir = "{$base_dir}/subdir";
        $file_path = "{$sub_dir}/testfile.txt";
        $outputer = new FakeOutputer();

        if (!is_dir($sub_dir)) {
            mkdir($sub_dir, 0777, true);
        }

        $this->assertTrue(is_dir($sub_dir), 'Directory should exist before calling create_folder_if_needed');

        create_folder_if_needed($file_path, $outputer);

        $this->assertTrue(is_dir($sub_dir), 'Directory should still exist after calling create_folder_if_needed');
        $this->assertSame('', $outputer->output, 'Outputer should not contain creation message when directory exists');
    }

    public function testMoveFileCreatesDirectoryAndMovesFile(): void
    {
        $base_dir = '/tmp/radar_test_move_folder';
        $sub_dir = "{$base_dir}/subdir";
        $src_file = "{$base_dir}/from.txt";
        $dest_file = "{$sub_dir}/to.txt";
        $outputer = new FakeOutputer();

        if (!is_dir($base_dir)) {
            mkdir($base_dir, 0777, true);
        }
        if (is_file($dest_file)) {
            unlink($dest_file);
        }
        if (is_dir($sub_dir)) {
            rmdir($sub_dir);
        }

        file_put_contents($src_file, 'testdata');
        $this->assertTrue(is_file($src_file), 'Source file should exist before moving');
        $this->assertFalse(is_dir($sub_dir), 'Destination directory should not exist before moving');

        move_file($src_file, $dest_file, $outputer);

        $this->assertTrue(is_dir($sub_dir), 'Destination directory should be created');
        $this->assertTrue(is_file($dest_file), 'Destination file should exist after moving');
        $this->assertEquals('testdata', file_get_contents($dest_file), 'Destination file should contain source file content');
        $this->assertFalse(is_file($src_file), 'Source file should not exist after moving');
        $this->assertEquals(
            <<<TXT
                Creating folder : /tmp/radar_test_move_folder/subdir
                Moving /tmp/radar_test_move_folder/from.txt to /tmp/radar_test_move_folder/subdir/to.txt\n
                TXT,
            $outputer->output,
            'Outputer should contain creation and move messages'
        );
    }

    public function testMoveFileDirectoryAndFileAlreadyExist(): void
    {
        $base_dir = '/tmp/radar_test_move_folder';
        $sub_dir = "{$base_dir}/subdir";
        $src_file = "{$base_dir}/from.txt";
        $dest_file = "{$sub_dir}/to.txt";
        $outputer = new FakeOutputer();

        if (!is_dir($sub_dir)) {
            mkdir($sub_dir, 0777, true);
        }

        file_put_contents($src_file, 'testdata');
        file_put_contents($dest_file, 'before');
        $this->assertTrue(is_dir($sub_dir), 'Destination directory should exist before moving');
        $this->assertTrue(is_file($src_file), 'Source file should exist before moving');
        $this->assertTrue(is_file($dest_file), 'Dest file should already exist');

        move_file($src_file, $dest_file, $outputer);

        $this->assertTrue(is_dir($sub_dir), 'Destination directory should still exist');
        $this->assertTrue(is_file($dest_file), 'Destination file should exist after moving');
        $this->assertEquals('testdata', file_get_contents($dest_file), 'Destination file should contain source file content');
        $this->assertFalse(is_file($src_file), 'Source file should not exist after moving');
        $this->assertEquals(
            "Moving /tmp/radar_test_move_folder/from.txt to /tmp/radar_test_move_folder/subdir/to.txt\n",
            $outputer->output,
            'Outputer should contain only move message when directory exists'
        );
    }

    public function testDownloadDataTypeForZone_whenNoContentDisposition(): void
    {
        $zone = 'METROPOLE';
        $data_type = 'LAME_D_EAU';
        $maille = 500;
        $replace_existing = false;
        $api_file_downloader = new InMemoryAPIFileDownloader([
            'https://public-api.meteofrance.fr/public/DPRadar/v1/mosaiques/METROPOLE/observations/LAME_D_EAU/produit?maille=500' => new CurlResponse(200, '', ['key' => 'value']),
        ]);
        $file_appender = new InMemoryFileAppender();
        $file_mover = new InMemoryFileMover();
        $last_tiles_timestamps_repository = new InMemoryLastTilesTimestampsRepository();
        $outputer = new FakeOutputer();
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
        $this->assertSame(
            [
                [
                    'path'    => '/tmp/mosaiques_MF_LAME_D_EAU_METROPOLE_last.h5',
                    'url'     => 'https://public-api.meteofrance.fr/public/DPRadar/v1/mosaiques/METROPOLE/observations/LAME_D_EAU/produit?maille=500',
                    'headers' => [],
                    'options' => [],
                ],
            ],
            $api_file_downloader->requests
        );
        $this->assertSame(
            [
                '/var/log/infoclimat/radar.log' => [
                    <<<TXT
                        Zone = METROPOLE, Type = LAME_D_EAU, Maille = 500, Response = CurlResponse(
                            code = 200,
                            response = '',
                            headers = {"key":"value"},
                            error_code = 0,
                            error = ''
                        )
                        TXT
                    ,
                ],
            ],
            $file_appender->files
        );
        $this->assertSame([], $file_mover->moved);
        $this->assertSame([], $last_tiles_timestamps_repository->timestamps);
        $ROOT = __ROOT__;
        $this->assertSame(
            <<<TXT
                Downloading LAME_D_EAU of METROPOLE (maille 500) [https://public-api.meteofrance.fr/public/DPRadar/v1/mosaiques/METROPOLE/observations/LAME_D_EAU/produit?maille=500] to /tmp/mosaiques_MF_LAME_D_EAU_METROPOLE_last.h5
                ERROR : Zone = METROPOLE, Type = LAME_D_EAU, Maille = 500, Response = CurlResponse(
                    code = 200,
                    response = '',
                    headers = {"key":"value"},
                    error_code = 0,
                    error = ''
                )
                LAME_D_EAU of METROPOLE : ERROR\n\n
                TXT,
            $outputer->output
        );
    }

    public function testDownloadDataTypeForZone_whenAlreadyUpToDate(): void
    {
        $zone = 'METROPOLE';
        $data_type = 'LAME_D_EAU';
        $maille = 500;
        $replace_existing = false;
        $api_file_downloader = new InMemoryAPIFileDownloader([
            'https://public-api.meteofrance.fr/public/DPRadar/v1/mosaiques/METROPOLE/observations/LAME_D_EAU/produit?maille=500' => new CurlResponse(200, '', ['content-disposition' => 'attachment; filename="T_IPRN20_C_LFPW_20000615123045.h5"']),
        ]);
        $file_appender = new InMemoryFileAppender();
        $file_mover = new InMemoryFileMover();
        $last_tiles_timestamps_repository = new InMemoryLastTilesTimestampsRepository(
            ['mosaiques_MF_LAME_D_EAU_METROPOLE' => strtotime('2000-06-15T12:30:45Z')]
        );
        $outputer = new FakeOutputer();
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
        $this->assertSame(
            [
                [
                    'path'    => '/tmp/mosaiques_MF_LAME_D_EAU_METROPOLE_last.h5',
                    'url'     => 'https://public-api.meteofrance.fr/public/DPRadar/v1/mosaiques/METROPOLE/observations/LAME_D_EAU/produit?maille=500',
                    'headers' => [],
                    'options' => [],
                ],
            ],
            $api_file_downloader->requests
        );
        $this->assertSame([], $file_mover->moved);
        $this->assertSame(
            ['mosaiques_MF_LAME_D_EAU_METROPOLE' => strtotime('2000-06-15T12:30:45Z')],
            $last_tiles_timestamps_repository->timestamps
        );
        $ROOT = __ROOT__;
        $this->assertSame(
            <<<TXT
                Downloading LAME_D_EAU of METROPOLE (maille 500) [https://public-api.meteofrance.fr/public/DPRadar/v1/mosaiques/METROPOLE/observations/LAME_D_EAU/produit?maille=500] to /tmp/mosaiques_MF_LAME_D_EAU_METROPOLE_last.h5
                Date from content-disposition header is : 20000615123045 (2000-06-15 12:30:45 UTC [961072245])
                Skipping LAME_D_EAU of METROPOLE (maille 500) at 961072245 because it is not newer than 961072245 and replace mode is not active.
                LAME_D_EAU of METROPOLE at 961072245 : SKIPPED\n\n
                TXT,
            $outputer->output
        );
    }

    public function testDownloadDataTypeForZone_whenThereIsNoPrevious(): void
    {
        $zone = 'METROPOLE';
        $data_type = 'LAME_D_EAU';
        $maille = 500;
        $replace_existing = false;
        $api_file_downloader = new InMemoryAPIFileDownloader([
            'https://public-api.meteofrance.fr/public/DPRadar/v1/mosaiques/METROPOLE/observations/LAME_D_EAU/produit?maille=500' => new CurlResponse(200, '', ['content-disposition' => 'attachment; filename="T_IPRN20_C_LFPW_20000615123045.h5"']),
        ]);
        $file_appender = new InMemoryFileAppender();
        $file_mover = new InMemoryFileMover();
        $last_tiles_timestamps_repository = new InMemoryLastTilesTimestampsRepository();
        $outputer = new FakeOutputer();
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
        $this->assertSame(
            [
                [
                    'path'    => '/tmp/mosaiques_MF_LAME_D_EAU_METROPOLE_last.h5',
                    'url'     => 'https://public-api.meteofrance.fr/public/DPRadar/v1/mosaiques/METROPOLE/observations/LAME_D_EAU/produit?maille=500',
                    'headers' => [],
                    'options' => [],
                ],
            ],
            $api_file_downloader->requests
        );
        $this->assertSame(
            [
                [
                    '/tmp/mosaiques_MF_LAME_D_EAU_METROPOLE_last.h5',
                    TILES_PATH . '/2000/06/15/mosaiques_MF_LAME_D_EAU_METROPOLE_12_v30.h5',
                    null,
                ],
            ],
            $file_mover->moved
        );
        $this->assertSame(
            ['mosaiques_MF_LAME_D_EAU_METROPOLE' => strtotime('2000-06-15T12:30:45Z')],
            $last_tiles_timestamps_repository->timestamps
        );
        $ROOT = __ROOT__;
        $TILES_PATH = TILES_PATH;
        $this->assertSame(
            <<<TXT
                Downloading LAME_D_EAU of METROPOLE (maille 500) [https://public-api.meteofrance.fr/public/DPRadar/v1/mosaiques/METROPOLE/observations/LAME_D_EAU/produit?maille=500] to /tmp/mosaiques_MF_LAME_D_EAU_METROPOLE_last.h5
                Date from content-disposition header is : 20000615123045 (2000-06-15 12:30:45 UTC [961072245])
                Moving /tmp/mosaiques_MF_LAME_D_EAU_METROPOLE_last.h5 to {$TILES_PATH}/2000/06/15/mosaiques_MF_LAME_D_EAU_METROPOLE_12_v30.h5
                Updating mosaiques_MF_LAME_D_EAU_METROPOLE to 961072245
                LAME_D_EAU of METROPOLE at 961072245 : DONE\n\n
                TXT,
            $outputer->output
        );
    }

    public function testDownloadDataTypeForZone(): void
    {
        $zone = 'METROPOLE';
        $data_type = 'LAME_D_EAU';
        $maille = 500;
        $replace_existing = false;
        $api_file_downloader = new InMemoryAPIFileDownloader([
            'https://public-api.meteofrance.fr/public/DPRadar/v1/mosaiques/METROPOLE/observations/LAME_D_EAU/produit?maille=500' => new CurlResponse(200, '', ['content-disposition' => 'attachment; filename="T_IPRN20_C_LFPW_20000615123045.h5"']),
        ]);
        $file_appender = new InMemoryFileAppender();
        $file_mover = new InMemoryFileMover();
        $last_tiles_timestamps_repository = new InMemoryLastTilesTimestampsRepository(
            ['mosaiques_MF_LAME_D_EAU_METROPOLE' => strtotime('2000-06-15T12:25:45Z')]
        );
        $outputer = new FakeOutputer();
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
        $this->assertSame(
            [
                [
                    'path'    => '/tmp/mosaiques_MF_LAME_D_EAU_METROPOLE_last.h5',
                    'url'     => 'https://public-api.meteofrance.fr/public/DPRadar/v1/mosaiques/METROPOLE/observations/LAME_D_EAU/produit?maille=500',
                    'headers' => [],
                    'options' => [],
                ],
            ],
            $api_file_downloader->requests
        );
        $this->assertSame(
            [
                [
                    '/tmp/mosaiques_MF_LAME_D_EAU_METROPOLE_last.h5',
                    TILES_PATH . '/2000/06/15/mosaiques_MF_LAME_D_EAU_METROPOLE_12_v30.h5',
                    null,
                ],
            ],
            $file_mover->moved
        );
        $this->assertSame(
            ['mosaiques_MF_LAME_D_EAU_METROPOLE' => strtotime('2000-06-15T12:30:45Z')],
            $last_tiles_timestamps_repository->timestamps
        );
        $TILES_PATH = TILES_PATH;
        $this->assertSame(
            <<<TXT
                Downloading LAME_D_EAU of METROPOLE (maille 500) [https://public-api.meteofrance.fr/public/DPRadar/v1/mosaiques/METROPOLE/observations/LAME_D_EAU/produit?maille=500] to /tmp/mosaiques_MF_LAME_D_EAU_METROPOLE_last.h5
                Date from content-disposition header is : 20000615123045 (2000-06-15 12:30:45 UTC [961072245])
                Moving /tmp/mosaiques_MF_LAME_D_EAU_METROPOLE_last.h5 to {$TILES_PATH}/2000/06/15/mosaiques_MF_LAME_D_EAU_METROPOLE_12_v30.h5
                Updating mosaiques_MF_LAME_D_EAU_METROPOLE to 961072245
                LAME_D_EAU of METROPOLE at 961072245 : DONE\n\n
                TXT,
            $outputer->output
        );
    }

    public function testDownloadDataType(): void
    {
        $data_type = 'LAME_D_EAU';
        $maille = 500;
        $replace_existing = false;
        $api_file_downloader = new InMemoryAPIFileDownloader([
            'https://public-api.meteofrance.fr/public/DPRadar/v1/mosaiques/ANTILLES/observations/LAME_D_EAU/produit?maille=500'  => new CurlResponse(200, '', ['content-disposition' => 'attachment; filename="T_IPRN20_C_LFPW_20000615123045.h5"']),
            'https://public-api.meteofrance.fr/public/DPRadar/v1/mosaiques/REUNION/observations/LAME_D_EAU/produit?maille=500'   => new CurlResponse(200, '', ['content-disposition' => 'attachment; filename="T_IPRN20_C_LFPW_20000615123045.h5"']),
            'https://public-api.meteofrance.fr/public/DPRadar/v1/mosaiques/METROPOLE/observations/LAME_D_EAU/produit?maille=500' => new CurlResponse(200, '', ['content-disposition' => 'attachment; filename="T_IPRN20_C_LFPW_20000615123045.h5"']),
            // 'https://public-api.meteofrance.fr/public/DPRadar/v1/mosaiques/NOUVELLE-CALEDONIE/observations/LAME_D_EAU/produit?maille=500' => new CurlResponse(200, '', ['key' => 'value']),
        ]);
        $file_appender = new InMemoryFileAppender();
        $file_mover = new InMemoryFileMover();
        $last_tiles_timestamps_repository = new InMemoryLastTilesTimestampsRepository([
            'mosaiques_MF_LAME_D_EAU_METROPOLE' => strtotime('2000-06-15T12:30:45Z'),
            'mosaiques_MF_LAME_D_EAU_REUNION'   => strtotime('2000-06-15T12:25:45Z'),
        ]);
        $outputer = new FakeOutputer();
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
        $this->assertSame(
            [
                [
                    'path'    => '/tmp/mosaiques_MF_LAME_D_EAU_ANTILLES_last.h5',
                    'url'     => 'https://public-api.meteofrance.fr/public/DPRadar/v1/mosaiques/ANTILLES/observations/LAME_D_EAU/produit?maille=500',
                    'headers' => [],
                    'options' => [],
                ],
                [
                    'path'    => '/tmp/mosaiques_MF_LAME_D_EAU_REUNION_last.h5',
                    'url'     => 'https://public-api.meteofrance.fr/public/DPRadar/v1/mosaiques/REUNION/observations/LAME_D_EAU/produit?maille=500',
                    'headers' => [],
                    'options' => [],
                ],
                [
                    'path'    => '/tmp/mosaiques_MF_LAME_D_EAU_METROPOLE_last.h5',
                    'url'     => 'https://public-api.meteofrance.fr/public/DPRadar/v1/mosaiques/METROPOLE/observations/LAME_D_EAU/produit?maille=500',
                    'headers' => [],
                    'options' => [],
                ],
                // [
                //     'path'    => '/tmp/mosaiques_MF_LAME_D_EAU_NOUVELLE-CALEDONIE_last.h5',
                //     'url'     => 'https://public-api.meteofrance.fr/public/DPRadar/v1/mosaiques/NOUVELLE-CALEDONIE/observations/LAME_D_EAU/produit?maille=500',
                //     'headers' => [],
                //     'options' => [],
                // ],
            ],
            $api_file_downloader->requests
        );
        $this->assertSame(
            [
                [
                    '/tmp/mosaiques_MF_LAME_D_EAU_ANTILLES_last.h5',
                    TILES_PATH . '/2000/06/15/mosaiques_MF_LAME_D_EAU_ANTILLES_12_v30.h5',
                    null,
                ],
                [
                    '/tmp/mosaiques_MF_LAME_D_EAU_REUNION_last.h5',
                    TILES_PATH . '/2000/06/15/mosaiques_MF_LAME_D_EAU_REUNION_12_v30.h5',
                    null,
                ],
            ],
            $file_mover->moved
        );
        $this->assertSame(
            [
                'mosaiques_MF_LAME_D_EAU_METROPOLE' => strtotime('2000-06-15T12:30:45Z'),
                'mosaiques_MF_LAME_D_EAU_REUNION'   => strtotime('2000-06-15T12:30:45Z'),
                'mosaiques_MF_LAME_D_EAU_ANTILLES'  => strtotime('2000-06-15T12:30:45Z'),
            ],
            $last_tiles_timestamps_repository->timestamps
        );
        $ROOT = __ROOT__;
        $TILES_PATH = TILES_PATH;
        $this->assertSame(
            <<<TXT
                Downloading LAME_D_EAU of ANTILLES (maille 500) [https://public-api.meteofrance.fr/public/DPRadar/v1/mosaiques/ANTILLES/observations/LAME_D_EAU/produit?maille=500] to /tmp/mosaiques_MF_LAME_D_EAU_ANTILLES_last.h5
                Date from content-disposition header is : 20000615123045 (2000-06-15 12:30:45 UTC [961072245])
                Moving /tmp/mosaiques_MF_LAME_D_EAU_ANTILLES_last.h5 to {$TILES_PATH}/2000/06/15/mosaiques_MF_LAME_D_EAU_ANTILLES_12_v30.h5
                Updating mosaiques_MF_LAME_D_EAU_ANTILLES to 961072245
                LAME_D_EAU of ANTILLES at 961072245 : DONE
                
                Downloading LAME_D_EAU of REUNION (maille 500) [https://public-api.meteofrance.fr/public/DPRadar/v1/mosaiques/REUNION/observations/LAME_D_EAU/produit?maille=500] to /tmp/mosaiques_MF_LAME_D_EAU_REUNION_last.h5
                Date from content-disposition header is : 20000615123045 (2000-06-15 12:30:45 UTC [961072245])
                Moving /tmp/mosaiques_MF_LAME_D_EAU_REUNION_last.h5 to {$TILES_PATH}/2000/06/15/mosaiques_MF_LAME_D_EAU_REUNION_12_v30.h5
                Updating mosaiques_MF_LAME_D_EAU_REUNION to 961072245
                LAME_D_EAU of REUNION at 961072245 : DONE
                
                Downloading LAME_D_EAU of METROPOLE (maille 500) [https://public-api.meteofrance.fr/public/DPRadar/v1/mosaiques/METROPOLE/observations/LAME_D_EAU/produit?maille=500] to /tmp/mosaiques_MF_LAME_D_EAU_METROPOLE_last.h5
                Date from content-disposition header is : 20000615123045 (2000-06-15 12:30:45 UTC [961072245])
                Skipping LAME_D_EAU of METROPOLE (maille 500) at 961072245 because it is not newer than 961072245 and replace mode is not active.
                LAME_D_EAU of METROPOLE at 961072245 : SKIPPED\n\n
                TXT,
// Downloading LAME_D_EAU of NOUVELLE-CALEDONIE (maille 500) [https://public-api.meteofrance.fr/public/DPRadar/v1/mosaiques/NOUVELLE-CALEDONIE/observations/LAME_D_EAU/produit?maille=500] to /tmp/mosaiques_MF_LAME_D_EAU_NOUVELLE-CALEDONIE_last.h5
// ERROR : Zone = NOUVELLE-CALEDONIE, Type = LAME_D_EAU, Maille = 500, Response = CurlResponse(code = 200, response = '', headers = {"key":"value"})
// LAME_D_EAU of NOUVELLE-CALEDONIE : ERROR
            $outputer->output
        );
    }

    public function testName(): void
    {
        $data = [];
        $expected = [];
        $this->assertSame($expected, $data);
        $this->assertNull(null);
        $this->assertSame('2000-06-15 12:30:00', '2000-06-15 12:30:00');
    }
}
