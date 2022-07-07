package com.summer.stockproject.service;

import com.summer.stockproject.dao.AAPLRepository;
import com.summer.stockproject.entity.AAPL;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;

@Service
public class AAPLServiceImpl implements AAPLService {

    private AAPLRepository aAPLRepository;

    @Autowired
    public AAPLServiceImpl(AAPLRepository AAPLRepository) {
        this.aAPLRepository = AAPLRepository;
    }

    @Override
    public List<AAPL> findAll() {
        return aAPLRepository.findAll();
    }

    @Override
    public AAPL getByTimePoint(LocalDateTime timepoint) {
        return aAPLRepository.getByTimePoint(timepoint);
    }

    @Override
    public AAPL getById(int theid) {
        return aAPLRepository.getById(theid);
    }


}
