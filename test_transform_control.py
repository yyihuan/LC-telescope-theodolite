import unittest
from datetime import datetime, timedelta
from astropy import units as u
from astropy.coordinates import EarthLocation, SkyCoord, AltAz
from astropy.time import Time
import numpy as np
import time

class TestCoordinateTransform(unittest.TestCase):
    def setUp(self):
        # 测试地点：北京天文台（经度：116.3912°E，纬度：39.9075°N）
        self.lat = 39.9075
        self.lon = 116.3912
        # 测试时间：2024年3月15日 20:00:00
        self.test_time = datetime(2024, 3, 15, 20, 0, 0)

    def equatorial_to_horizontal(self, ra, dec, lat, lon, time):
        """
        使用astropy将赤道坐标系转换为地平坐标系。

        :param ra: 赤经 (小时)
        :param dec: 赤纬 (度)
        :param lat: 观测点纬度 (度)
        :param lon: 观测点经度 (度)
        :param time: 观测时间 (datetime对象)
        :return: 方位角 (度), 高度角 (度)
        """
        # 定义观测地点
        location = EarthLocation(lat=lat*u.deg, lon=lon*u.deg)
        # 定义观测时间
        astropy_time = Time(time)
        # 定义赤道坐标
        equatorial_coord = SkyCoord(ra=ra*15*u.deg, dec=dec*u.deg)
        # 定义地平坐标系
        altaz_frame = AltAz(obstime=astropy_time, location=location)
        # 转换为地平坐标
        altaz_coord = equatorial_coord.transform_to(altaz_frame)

        return altaz_coord.az.deg, altaz_coord.alt.deg

    def test_north_point(self):
        """测试北天极的转换"""
        # 北天极的赤道坐标
        ra = 0.0
        dec = 90.0
        az, alt = self.equatorial_to_horizontal(ra, dec, self.lat, self.lon, self.test_time)
        # 北天极的高度角应该等于纬度
        self.assertAlmostEqual(alt, self.lat, delta=1.0)
        # 方位角应该接近0度（正北）或360度
        self.assertTrue(az < 1.0 or az > 359.0, f"方位角 {az} 不接近北方")

    def test_south_point(self):
        """测试南天极的转换"""
        # 南天极的赤道坐标
        ra = 0.0
        dec = -90.0
        az, alt = self.equatorial_to_horizontal(ra, dec, self.lat, self.lon, self.test_time)
        # 南天极的高度角应该等于负的纬度
        self.assertAlmostEqual(alt, -self.lat, delta=1.0)
        # 方位角应该接近180度（正南）
        self.assertAlmostEqual(az, 180.0, delta=1.0)

    def test_equator_point(self):
        """测试赤道上的点的转换"""
        # 赤道上的一个点
        ra = 6.0  # 赤经
        dec = 0.0  # 赤纬
        az, alt = self.equatorial_to_horizontal(ra, dec, self.lat, self.lon, self.test_time)
        # 高度角应该在合理范围内（-90到90度）
        self.assertTrue(-90 <= alt <= 90)
        # 方位角应该在合理范围内（0到360度）
        self.assertTrue(0 <= az <= 360)

    def test_local_sky_coordinates(self):
        """测试当地天空中不同点的坐标转换"""
        test_cases = [
            # 赤经(小时), 赤纬(度)
            (0.0, 30.0),    # 子午线上高于赤道的点
            (6.0, 45.0),    # 东方高角度的点
            (12.0, 15.0),   # 南方低角度的点
            (18.0, 60.0),   # 西方高角度的点
        ]
        
        for ra, dec in test_cases:
            with self.subTest(ra=ra, dec=dec):
                az, alt = self.equatorial_to_horizontal(ra, dec, self.lat, self.lon, self.test_time)
                # 验证结果在有效范围内
                self.assertTrue(0 <= az <= 360, f"方位角 {az} 超出范围 [0, 360]")
                self.assertTrue(-90 <= alt <= 90, f"高度角 {alt} 超出范围 [-90, 90]")
    
    def test_known_stars(self):
        """测试已知恒星位置的转换"""
        # 测试几颗明亮的恒星
        stars = [
            # 名称, 赤经(小时), 赤纬(度)
            ("北极星", 2.53, 89.26),  # 北极星
            ("天狼星", 6.75, -16.72),  # 天狼星
            ("织女星", 18.62, 38.78),  # 织女星
            ("牛郎星", 19.85, 8.87),   # 牛郎星
        ]
        
        for name, ra, dec in stars:
            with self.subTest(star=name):
                az, alt = self.equatorial_to_horizontal(ra, dec, self.lat, self.lon, self.test_time)
                # 验证结果在有效范围内
                self.assertTrue(0 <= az <= 360, f"{name}的方位角 {az} 超出范围 [0, 360]")
                self.assertTrue(-90 <= alt <= 90, f"{name}的高度角 {alt} 超出范围 [-90, 90]")
                print(f"{name}: 赤经={ra}小时, 赤纬={dec}度 -> 方位角={az:.2f}度, 高度角={alt:.2f}度")

    def test_time_sequence(self):
        """测试指定参数随时间变化的坐标转换"""
        # 指定参数
        ra = 90.0 / 15.0  # 将90度转换为小时（1小时=15度）
        dec = 45.0
        lat = 40.011
        lon = 116.392
        
        print("\n测试指定参数随时间的变化：")
        print(f"赤经: {ra*15}度 ({ra}小时), 赤纬: {dec}度")
        print(f"观测地点: 经度 {lon}度, 纬度 {lat}度")
        print("时间序列测试结果（每10秒一次，共15次）：")
        print("序号 | 时间 | 方位角(度) | 高度角(度)")
        print("-" * 50)
        
        # 获取当前时间作为起始时间
        current_time = datetime.now()
        
        # 进行15次测试，每次间隔10秒
        for i in range(15):
            # 计算测试时间（当前时间 + i*10秒）
            test_time = current_time + timedelta(seconds=i*10)
            
            # 执行坐标转换
            az, alt = self.equatorial_to_horizontal(ra, dec, lat, lon, test_time)
            
            # 打印结果
            print(f"{i+1:2d} | {test_time.strftime('%H:%M:%S')} | {az:10.5f} | {alt:10.5f}")
            
            # 等待10秒
            if i < 14:  # 最后一次不需要等待
                time.sleep(10)
            
        # 验证结果在有效范围内
        self.assertTrue(0 <= az <= 360, f"方位角 {az} 超出范围 [0, 360]")
        self.assertTrue(-90 <= alt <= 90, f"高度角 {alt} 超出范围 [-90, 90]")

if __name__ == '__main__':
    unittest.main() 